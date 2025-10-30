from fastapi import FastAPI
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from text_cleaner import TextCleaner
import pickle
import mlflow
import time
import os
import numpy as np

MODEL_PATH = "models/ensemble_model.pkl"
ENCODER_PATH = "models/label_encoder.pkl"
VECTORIZER_PATH = "models/vectorizer.pkl"
MLFLOW_TRACKING_URI = "http://localhost:5000"
MLFLOW_EXPERIMENT_NAME = "instance_experiment"

app = FastAPI(
    title="Fake News Detector API",
    description="🚀 An ensemble-based fake news detection model deployed with FastAPI, MLflow & Waitress",
    version="1.0"
)

templates = Jinja2Templates(directory="templates")

print("🔄 Loading model and encoder...")

with open('models/ensemble_model.pkl', 'rb') as f:
    model = pickle.load(f)

with open('models/label_encoder.pkl', 'rb') as f:
    encoder = pickle.load(f)

with open('models/vectorizer.pkl', 'rb') as f:
    vectorizer = pickle.load(f)

print("✅ Model, Encoder, and Vectorizer loaded successfully!")

mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
try:
    experiment_id = mlflow.create_experiment(MLFLOW_EXPERIMENT_NAME)
except mlflow.exceptions.RestException:
    experiment = mlflow.get_experiment_by_name(MLFLOW_EXPERIMENT_NAME)
    experiment_id = experiment.experiment_id


class NewsItem(BaseModel):
    title: str
    text: str

@app.get("/", response_class=HTMLResponse)
def serve_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/predict")
def predict(news: NewsItem):
    """
    Endpoint for predicting if a news article is REAL or FAKE.
    """
    start_time = time.time()

    full_text = news.title + " " + news.text

    if vectorizer:
        X_input = vectorizer.transform([full_text])
    else:
        X_input = [full_text] 

    prediction = model.predict(X_input)[0]
    proba = None
    if hasattr(model, "predict_proba"):
        try:
            proba = np.max(model.predict_proba(X_input))
        except Exception:
            proba = 0.0

    decoded_label = encoder.inverse_transform([prediction])[0].upper()

    latency = round(time.time() - start_time, 3)

    with mlflow.start_run(experiment_id=experiment_id, run_name="inference_instance"):
        mlflow.log_param("title_length", len(news.title))
        mlflow.log_param("text_length", len(news.text))
        mlflow.log_metric("latency_sec", latency)
        if proba is not None:
            mlflow.log_metric("confidence", float(proba))
        mlflow.log_param("model_version", "v1_ensemble")

    return {
        "prediction": decoded_label,
        "confidence": round(float(proba), 3) if proba else None,
        "latency_seconds": latency
    }
