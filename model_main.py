import pandas as pd
import mlflow
import mlflow.sklearn
import re
import pickle
import os

from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from xgboost import XGBClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, classification_report
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder
from text_cleaner import TextCleaner

data_path = "fake_news_dataset.csv" 
df = pd.read_csv(data_path)

df['combined_text'] = df['title'].fillna('') + " " + df['text'].fillna('')

df = df.dropna(subset=['label'])

print(f"✅ Loaded dataset with {len(df)} samples.")

X_train, X_test, y_train, y_test = train_test_split(
    df['combined_text'], df['label'], test_size=0.2, random_state=42, stratify=df['label']
)

log_reg = LogisticRegression(max_iter=1000, random_state=42)
rand_forest = RandomForestClassifier(n_estimators=200, random_state=42)
xgb = XGBClassifier(use_label_encoder=False, eval_metric='logloss', random_state=42)

with open('models/vectorizer.pkl', 'wb') as f:
    pickle.dump(TfidfVectorizer(max_features=8000, stop_words='english'), f)

ensemble = VotingClassifier(
    estimators=[
        ('lr', log_reg),
        ('rf', rand_forest),
        ('xgb', xgb)
    ],
    voting='soft'
)

pipeline = Pipeline([
    ('cleaner', TextCleaner()),
    ('tfidf', TfidfVectorizer(max_features=8000, stop_words='english')),
    ('ensemble', ensemble)
])

if y_train.dtype == 'object':
    label_encoder = LabelEncoder()
    y_train = label_encoder.fit_transform(y_train)
    y_test = label_encoder.transform(y_test)
    print("✅ Label encoding applied:", dict(zip(label_encoder.classes_, label_encoder.transform(label_encoder.classes_))))
    os.makedirs("models", exist_ok=True)
    with open('models/encoder.pkl', 'wb') as f:
        pickle.dump(label_encoder, f)

mlflow.set_tracking_uri("http://localhost:5000")  
mlflow.set_experiment("FakeNewsEnsemble")

with mlflow.start_run(run_name="Ensemble_Voting_Model"):
    
    mlflow.log_param("vectorizer", "TF-IDF")
    mlflow.log_param("max_features", 8000)
    mlflow.log_param("models", "LogisticRegression, RandomForest, XGBoost")
    mlflow.log_param("voting", "soft")

    print("🚀 Training ensemble model...")
    pipeline.fit(X_train, y_train)

    preds = pipeline.predict(X_test)

    acc = accuracy_score(y_test, preds)
    prec = precision_score(y_test, preds, pos_label=1)
    rec = recall_score(y_test, preds, pos_label=1)
    f1 = f1_score(y_test, preds, pos_label=1)

    mlflow.log_metric("accuracy", acc)
    mlflow.log_metric("precision", prec)
    mlflow.log_metric("recall", rec)
    mlflow.log_metric("f1_score", f1)

    print("\n📊 Classification Report:")
    print(classification_report(y_test, preds, target_names=label_encoder.classes_ if 'label_encoder' in locals() else None))

    mlflow.sklearn.log_model(pipeline, "ensemble_model")

    os.makedirs("models", exist_ok=True)
    with open('models/ensemble_model.pkl', 'wb') as f:
        pickle.dump(pipeline, f)
    print("💾 Model saved as models/ensemble_model.pkl")

print("✅ Training complete! Accuracy:", round(acc * 100, 2), "%")