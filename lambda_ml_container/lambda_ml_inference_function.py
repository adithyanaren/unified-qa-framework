import json
import joblib
import numpy as np
import boto3
import os
import tempfile
import time

# === S3 + CloudWatch details ===
S3_BUCKET = "qaframework-ml-bucket-976193248434"
MODEL_KEY = "heart_disease_xgb_model.pkl"
CLOUDWATCH_NAMESPACE = "QAFrameworkMetrics"

s3 = boto3.client("s3")
cloudwatch = boto3.client("cloudwatch")
model = None
cold_start = True  # <— flag for cold start count

try:
    tmp_path = os.path.join(tempfile.gettempdir(), MODEL_KEY)
    s3.download_file(S3_BUCKET, MODEL_KEY, tmp_path)
    model = joblib.load(tmp_path)
    print("✅ Model downloaded and loaded from S3.")
except Exception as e:
    print("❌ Failed to load model from S3:", e)


def publish_metric(name, value, unit="Count"):
    """Helper to push metrics to CloudWatch"""
    try:
        cloudwatch.put_metric_data(
            Namespace=CLOUDWATCH_NAMESPACE,
            MetricData=[
                {
                    "MetricName": name,
                    "Value": value,
                    "Unit": unit
                }
            ]
        )
        print(f"📈 Pushed metric: {name} = {value} ({unit})")
    except Exception as e:
        print(f"⚠️ Failed to publish {name}: {e}")


def lambda_handler(event, context):
    global cold_start
    start_time = time.time()

    try:
        # 🩺 Health check route
        route_key = event.get("routeKey", "")
        path = event.get("rawPath") or event.get("path") or ""
        if "health" in route_key or "/health" in path:
            return {
                "statusCode": 200,
                "body": json.dumps({
                    "status": "ok",
                    "message": "QA Framework ML Inference API is healthy"
                }),
            }

        body = json.loads(event["body"]) if "body" in event else event

        feature_names = [
            'Chest_Pain', 'Shortness_of_Breath', 'Fatigue', 'Palpitations',
            'Dizziness', 'Swelling', 'Pain_Arms_Jaw_Back', 'Cold_Sweats_Nausea',
            'High_BP', 'High_Cholesterol', 'Diabetes', 'Smoking', 'Obesity',
            'Sedentary_Lifestyle', 'Family_History', 'Chronic_Stress', 'Gender', 'Age'
        ]

        X_input = np.array([[body.get(f, 0) for f in feature_names]], dtype=float)
        X_input[:, -1] = X_input[:, -1] / 100.0  # scale Age

        if model is None:
            return {"statusCode": 500, "body": json.dumps({"error": "Model not loaded"})}

        pred_class = int(model.predict(X_input)[0])
        pred_prob = float(model.predict_proba(X_input)[0][1])

        # === Record metrics ===
        latency_ms = round((time.time() - start_time) * 1000, 2)
        publish_metric("InferenceCount", 1)
        publish_metric("InferenceLatency", latency_ms, unit="Milliseconds")
        if cold_start:
            publish_metric("ModelColdStartCount", 1)
            cold_start = False  # mark container as warm

        result = {
            "predicted_class": pred_class,
            "risk_probability": round(pred_prob, 3),
            "inference_latency_ms": latency_ms
        }

        return {"statusCode": 200, "body": json.dumps(result)}

    except Exception as e:
        print("❌ Error in inference:", str(e))
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
