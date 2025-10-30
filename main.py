from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from text_cleaner import TextCleaner
import pickle
import joblib
import mlflow
import time
import os
import numpy as np
import pandas as pd
import sys
from datetime import datetime
from typing import Optional

# Prometheus imports
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from prometheus_fastapi_instrumentator import Instrumentator
from starlette.responses import Response

# Import database
from database import get_db, Prediction, init_db

# Import all model classes needed for unpickling
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from sklearn.pipeline import Pipeline
from xgboost import XGBClassifier

# Ensure TextCleaner is available in the correct module namespace for unpickling
sys.modules['__main__'].TextCleaner = TextCleaner

MODEL_PATH = "models/ensemble_model.pkl"
ENCODER_PATH = "models/encoder.pkl"
# Support Docker environment variable for MLflow
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
MLFLOW_EXPERIMENT_NAME = "instance_experiment"

app = FastAPI(
    title="Fake News Detector API",
    description="🚀 An ensemble-based fake news detection model deployed with FastAPI, MLflow & Waitress",
    version="1.0"
)

# Add CORS middleware to allow browser access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

templates = Jinja2Templates(directory="templates")

# ========================================
# Prometheus Metrics Setup
# ========================================

# Custom metrics
predictions_counter = Counter(
    'fakenews_predictions_total',
    'Total number of predictions made',
    ['result']  # REAL or FAKE
)

prediction_latency = Histogram(
    'fakenews_prediction_latency_seconds',
    'Time spent processing prediction',
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0]
)

feedback_counter = Counter(
    'fakenews_feedback_total',
    'Total feedback submissions',
    ['feedback_type']  # correct or incorrect
)

rating_gauge = Gauge(
    'fakenews_average_rating',
    'Average user rating'
)

total_predictions_gauge = Gauge(
    'fakenews_total_predictions',
    'Total predictions in database'
)

accuracy_gauge = Gauge(
    'fakenews_model_accuracy',
    'Model accuracy based on user feedback'
)

fake_predictions_gauge = Gauge(
    'fakenews_fake_count',
    'Number of FAKE predictions'
)

real_predictions_gauge = Gauge(
    'fakenews_real_count',
    'Number of REAL predictions'
)

# Initialize Prometheus Instrumentator for automatic metrics
instrumentator = Instrumentator(
    should_group_status_codes=True,
    should_ignore_untemplated=True,
    should_respect_env_var=True,
    should_instrument_requests_inprogress=True,
    excluded_handlers=["/metrics"],
    env_var_name="ENABLE_METRICS",
    inprogress_name="fakenews_requests_inprogress",
    inprogress_labels=True,
)

# Instrument the FastAPI app
instrumentator.instrument(app)

print("🔄 Loading model and encoder...")

with open('models/ensemble_model.pkl', 'rb') as f:
    model = pickle.load(f)

with open('models/encoder.pkl', 'rb') as f:
    encoder = pickle.load(f)

print("✅ Model Pipeline and Encoder loaded successfully!")
print(f"📋 Pipeline steps: {[step[0] for step in model.steps]}")

experiment_id = None
try:
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)
    result = sock.connect_ex(('localhost', 5000))
    sock.close()
    
    if result == 0:
        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
        try:
            experiment_id = mlflow.create_experiment(MLFLOW_EXPERIMENT_NAME)
            print(f"✅ MLflow tracking initialized at {MLFLOW_TRACKING_URI}")
        except mlflow.exceptions.RestException:
            experiment = mlflow.get_experiment_by_name(MLFLOW_EXPERIMENT_NAME)
            experiment_id = experiment.experiment_id
            print(f"✅ MLflow experiment '{MLFLOW_EXPERIMENT_NAME}' found")
    else:
        print(f"⚠️ MLflow server not running on {MLFLOW_TRACKING_URI}")
        print("⚠️ Continuing without MLflow tracking...")
except Exception as e:
    print(f"⚠️ MLflow initialization failed: {e}")
    print("⚠️ Continuing without MLflow tracking...")

# Initialize database
init_db()


class NewsItem(BaseModel):
    title: str = "" 
    text: str


class FeedbackItem(BaseModel):
    prediction_id: int
    user_feedback: str  # 'correct' or 'incorrect'
    user_rating: int  # 1-5


@app.get("/", response_class=HTMLResponse)
def serve_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/dashboard", response_class=HTMLResponse)
def serve_dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.post("/predict")
def predict(news: NewsItem, db: Session = Depends(get_db)):
    """
    Endpoint for predicting if a news article is REAL or FAKE.
    """
    start_time = time.time()

    # Combine title and text (both fields now handled)
    full_text = news.title + " " + news.text

    # Use the PIPELINE directly - it includes TextCleaner, TfidfVectorizer, and Ensemble
    # The pipeline expects a pandas Series or list
    X_input = pd.Series([full_text])
    
    prediction = model.predict(X_input)[0]
    proba = None
    if hasattr(model, "predict_proba"):
        try:
            proba = np.max(model.predict_proba(X_input))
        except Exception:
            proba = 0.0

    decoded_label = encoder.inverse_transform([prediction])[0].upper()

    latency = round(time.time() - start_time, 3)
    
    # ========================================
    # Update Prometheus Metrics
    # ========================================
    predictions_counter.labels(result=decoded_label).inc()
    prediction_latency.observe(latency)
    
    # Update gauges based on database
    if decoded_label == "FAKE":
        fake_predictions_gauge.inc()
    else:
        real_predictions_gauge.inc()

    # Log to MLflow only if available
    if experiment_id is not None:
        try:
            with mlflow.start_run(experiment_id=experiment_id, run_name="inference_instance"):
                mlflow.log_param("title_length", len(news.title))
                mlflow.log_param("text_length", len(news.text))
                mlflow.log_metric("latency_sec", latency)
                if proba is not None:
                    mlflow.log_metric("confidence", float(proba))
                mlflow.log_param("model_version", "v1_ensemble")
        except Exception as e:
            print(f"⚠️ MLflow logging failed: {e}")

    # Save prediction to database
    try:
        db_prediction = Prediction(
            title=news.title,
            text=news.text,
            prediction=decoded_label,
            confidence=float(proba) if proba else 0.0,
            latency_seconds=latency,
            timestamp=datetime.utcnow()
        )
        db.add(db_prediction)
        db.commit()
        db.refresh(db_prediction)
        prediction_id = db_prediction.id
        print(f"✅ Prediction saved to database with ID: {prediction_id}")
    except Exception as e:
        print(f"⚠️ Database save failed: {e}")
        db.rollback()
        prediction_id = None

    return {
        "prediction_id": prediction_id,
        "prediction": decoded_label,
        "confidence": round(float(proba), 3) if proba else None,
        "latency_seconds": latency
    }


@app.post("/feedback")
def submit_feedback(feedback: FeedbackItem, db: Session = Depends(get_db)):
    """
    Endpoint for submitting user feedback on a prediction.
    """
    try:
        # Find the prediction by ID
        prediction = db.query(Prediction).filter(Prediction.id == feedback.prediction_id).first()
        
        if not prediction:
            raise HTTPException(status_code=404, detail="Prediction not found")
        
        # Validate feedback
        if feedback.user_feedback not in ["correct", "incorrect"]:
            raise HTTPException(status_code=400, detail="Feedback must be 'correct' or 'incorrect'")
        
        if feedback.user_rating < 1 or feedback.user_rating > 5:
            raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")
        
        # Update the prediction with feedback
        prediction.user_feedback = feedback.user_feedback
        prediction.user_rating = feedback.user_rating
        
        db.commit()
        
        # ========================================
        # Update Prometheus Metrics
        # ========================================
        feedback_counter.labels(feedback_type=feedback.user_feedback).inc()
        
        # Update accuracy and rating gauges
        update_metrics_from_db(db)
        
        print(f"✅ Feedback saved for prediction ID: {feedback.prediction_id}")
        
        return {
            "status": "success",
            "message": "Thank you for your feedback!",
            "prediction_id": feedback.prediction_id
        }
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"⚠️ Feedback submission failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to save feedback")


@app.get("/api/stats")
def get_statistics(db: Session = Depends(get_db)):
    """
    Get statistics for the dashboard.
    """
    try:
        # Total predictions
        total_predictions = db.query(Prediction).count()
        
        # Predictions with feedback
        predictions_with_feedback = db.query(Prediction).filter(
            Prediction.user_feedback.isnot(None)
        ).all()
        
        # Calculate accuracy (correct predictions / total with feedback)
        correct_predictions = len([p for p in predictions_with_feedback if p.user_feedback == "correct"])
        accuracy = (correct_predictions / len(predictions_with_feedback) * 100) if predictions_with_feedback else 0
        
        # Average rating
        ratings = [p.user_rating for p in db.query(Prediction).all() if p.user_rating is not None]
        avg_rating = sum(ratings) / len(ratings) if ratings else 0
        
        # Today's predictions
        today = datetime.utcnow().date()
        today_predictions = db.query(Prediction).filter(
            Prediction.timestamp >= datetime.combine(today, datetime.min.time())
        ).count()
        
        # Real vs Fake count
        real_count = db.query(Prediction).filter(Prediction.prediction == "REAL").count()
        fake_count = db.query(Prediction).filter(Prediction.prediction == "FAKE").count()
        
        return {
            "total_predictions": total_predictions,
            "accuracy": round(accuracy, 1),
            "average_rating": round(avg_rating, 1),
            "today_predictions": today_predictions,
            "real_count": real_count,
            "fake_count": fake_count,
            "feedback_count": len(predictions_with_feedback)
        }
    
    except Exception as e:
        print(f"⚠️ Stats retrieval failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve statistics")


@app.get("/api/predictions")
def get_predictions(limit: int = 50, db: Session = Depends(get_db)):
    """
    Get recent predictions for the dashboard table.
    """
    try:
        predictions = db.query(Prediction).order_by(
            Prediction.timestamp.desc()
        ).limit(limit).all()
        
        return {
            "predictions": [p.to_dict() for p in predictions]
        }
    
    except Exception as e:
        print(f"⚠️ Predictions retrieval failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve predictions")


# ========================================
# Prometheus Metrics Endpoint
# ========================================

@app.get("/metrics")
def metrics():
    """
    Prometheus metrics endpoint.
    This endpoint is scraped by Prometheus to collect all metrics.
    """
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


# ========================================
# Helper Functions
# ========================================

def update_metrics_from_db(db: Session):
    """
    Update Prometheus gauges from database statistics.
    Called after feedback submission to refresh metrics.
    """
    try:
        # Total predictions
        total = db.query(Prediction).count()
        total_predictions_gauge.set(total)
        
        # Predictions with feedback
        predictions_with_feedback = db.query(Prediction).filter(
            Prediction.user_feedback.isnot(None)
        ).all()
        
        # Calculate accuracy
        if predictions_with_feedback:
            correct = len([p for p in predictions_with_feedback if p.user_feedback == "correct"])
            accuracy = (correct / len(predictions_with_feedback)) * 100
            accuracy_gauge.set(accuracy)
        
        # Average rating
        ratings = [p.user_rating for p in db.query(Prediction).all() if p.user_rating is not None]
        if ratings:
            avg_rating = sum(ratings) / len(ratings)
            rating_gauge.set(avg_rating)
        
        # Real vs Fake counts
        real_count = db.query(Prediction).filter(Prediction.prediction == "REAL").count()
        fake_count = db.query(Prediction).filter(Prediction.prediction == "FAKE").count()
        real_predictions_gauge.set(real_count)
        fake_predictions_gauge.set(fake_count)
        
    except Exception as e:
        print(f"⚠️ Metrics update failed: {e}")


# ========================================
# Startup Event
# ========================================

@app.on_event("startup")
async def startup_event():
    """
    Initialize metrics on startup.
    """
    print("🚀 Initializing Prometheus metrics...")
    
    # Initialize metrics from database
    from database import SessionLocal
    db = SessionLocal()
    try:
        update_metrics_from_db(db)
        print("✅ Prometheus metrics initialized")
    except Exception as e:
        print(f"⚠️ Failed to initialize metrics: {e}")
    finally:
        db.close()
    
    # Expose metrics endpoint
    instrumentator.expose(app, endpoint="/metrics", include_in_schema=False)
    print("✅ Metrics endpoint exposed at /metrics")
