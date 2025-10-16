import json, joblib, numpy as np, boto3, os, tempfile, time

# ==========================================================
# Unified QA Framework – ML Inference Lambda (Stable v3)
# Fixes:
#  • Missing keys in response
#  • Invalid payload not handled (200 / 500)
#  • High-latency / cold-start consistency
# ==========================================================

S3_BUCKET = "qaframework-ml-bucket-976193248434"
MODEL_KEY = "heart_disease_xgb_model.pkl"
CLOUDWATCH_NAMESPACE = "QAFrameworkMetrics"

s3 = boto3.client("s3")
cloudwatch = boto3.client("cloudwatch")

model = None
cold_start = True


# === Utility Functions ===

def build_response(status: int, body_dict: dict):
    """Always return consistent API Gateway format."""
    return {"statusCode": status, "body": json.dumps(body_dict)}


def load_model():
    """Download once, reuse thereafter."""
    global model
    if model is not None:
        return model
    try:
        tmp_path = os.path.join(tempfile.gettempdir(), MODEL_KEY)
        s3.download_file(S3_BUCKET, MODEL_KEY, tmp_path)
        model = joblib.load(tmp_path)
        print("✅ Model loaded successfully from S3")
    except Exception as e:
        print(f"❌ Model load error: {e}")
        model = None
    return model


def publish_metric(name, value, unit="Count"):
    """Push metric safely to CloudWatch."""
    try:
        cloudwatch.put_metric_data(
            Namespace=CLOUDWATCH_NAMESPACE,
            MetricData=[{"MetricName": name, "Value": value, "Unit": unit}],
        )
    except Exception as e:
        print(f"⚠️ Metric publish failed: {e}")


def validate_input(data: dict):
    """Ensure all fields exist and are valid."""
    required = [
        "Chest_Pain", "Shortness_of_Breath", "Fatigue", "Palpitations",
        "Dizziness", "Swelling", "Pain_Arms_Jaw_Back", "Cold_Sweats_Nausea",
        "High_BP", "High_Cholesterol", "Diabetes", "Smoking", "Obesity",
        "Sedentary_Lifestyle", "Family_History", "Chronic_Stress",
        "Gender", "Age"
    ]
    for f in required:
        if f not in data:
            return f"Missing field: {f}"
        v = data[f]
        if not isinstance(v, (int, float)):
            return f"Invalid type for {f}"
        if f == "Age" and not (20 <= v <= 100):
            return "Age out of valid range (20–100)"
        if f != "Age" and v not in [0, 1]:
            return f"Invalid binary value for {f}"
    return None


# === Main Handler ===

def lambda_handler(event, context):
    global cold_start
    start = time.time()

    # ---- Health ----
    path = event.get("rawPath") or event.get("path") or ""
    if "health" in path:
        return build_response(200, {"status": "ok", "message": "QA Inference API healthy"})

    # ---- Load Model ----
    mdl = load_model()
    if mdl is None:
        return build_response(500, {"error": "Model not loaded"})

    # ---- Parse Body ----
    try:
        raw = event.get("body", "{}")
        body = json.loads(raw) if isinstance(raw, str) else raw
        if not isinstance(body, dict):
            raise ValueError("Body must be a JSON object")
    except Exception as e:
        return build_response(400, {"error": f"Invalid JSON: {str(e)}"})

    # ---- Validate ----
    err = validate_input(body)
    if err:
        return build_response(400, {"error": err})

    # ---- inference ----
    try:
        order = [
            "Chest_Pain", "Shortness_of_Breath", "Fatigue", "Palpitations",
            "Dizziness", "Swelling", "Pain_Arms_Jaw_Back", "Cold_Sweats_Nausea",
            "High_BP", "High_Cholesterol", "Diabetes", "Smoking", "Obesity",
            "Sedentary_Lifestyle", "Family_History", "Chronic_Stress",
            "Gender", "Age"
        ]
        X = np.array([[body[f] for f in order]], dtype=float)
        X[:, -1] /= 100.0  # normalize age

        try:
            pred = int(mdl.predict(X)[0])
            probas = mdl.predict_proba(X)[0]
            conf = float(probas[pred]) if len(probas) > pred else 0.0
        except Exception as e:
            print("⚠️ Inference computation failed:", str(e))
            return build_response(500, {"error": f"Inference computation failed: {str(e)}"})

        latency = round((time.time() - start) * 1000, 2)

        publish_metric("InferenceCount", 1)
        publish_metric("InferenceLatency", latency, "Milliseconds")
        if cold_start:
            publish_metric("ModelColdStartCount", 1)
            cold_start = False

        # --- Guarantee complete, valid response ---
        if not isinstance(pred, int) or not isinstance(conf, (float, int)):
            return build_response(500, {"error": "Invalid inference output types"})

        result = {
            "prediction": pred,
            "confidence": round(conf, 3),
            "latency_ms": latency
        }

        # Ensure every expected key exists
        expected = {"prediction", "confidence", "latency_ms"}
        if not expected.issubset(result.keys()):
            return build_response(500, {"error": "Incomplete inference response"})

        return build_response(200, result)

    except Exception as e:
        print("❌ Inference error:", str(e))
        return build_response(500, {"error": f"Inference failed: {str(e)}"})
