import json
import joblib
import numpy as np
import boto3
import os
import tempfile

# === S3 details ===
S3_BUCKET = "qaframework-ml-bucket-976193248434"
MODEL_KEY = "heart_disease_xgb_model.pkl"

# === Load model from S3 at cold start ===
s3 = boto3.client("s3")
model = None

try:
    tmp_path = os.path.join(tempfile.gettempdir(), MODEL_KEY)
    s3.download_file(S3_BUCKET, MODEL_KEY, tmp_path)
    model = joblib.load(tmp_path)
    print("✅ Model downloaded and loaded from S3.")
except Exception as e:
    print("❌ Failed to load model from S3:", e)

def lambda_handler(event, context):
    try:
        # Parse input JSON
        body = json.loads(event["body"]) if "body" in event else event

        # Feature order must match training
        feature_names = [
            'Chest_Pain', 'Shortness_of_Breath', 'Fatigue', 'Palpitations',
            'Dizziness', 'Swelling', 'Pain_Arms_Jaw_Back', 'Cold_Sweats_Nausea',
            'High_BP', 'High_Cholesterol', 'Diabetes', 'Smoking', 'Obesity',
            'Sedentary_Lifestyle', 'Family_History', 'Chronic_Stress', 'Gender', 'Age'
        ]

        X_input = np.array([[body.get(f, 0) for f in feature_names]])

        if model is None:
            return {"statusCode": 500, "body": json.dumps({"error": "Model not loaded"})}

        pred_class = int(model.predict(X_input)[0])
        pred_prob = float(model.predict_proba(X_input)[0][1])

        result = {
            "predicted_class": pred_class,
            "risk_probability": round(pred_prob, 3)
        }

        return {"statusCode": 200, "body": json.dumps(result)}

    except Exception as e:
        print("❌ Error in inference:", str(e))
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
