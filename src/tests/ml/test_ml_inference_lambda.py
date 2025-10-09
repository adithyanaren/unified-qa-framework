# /QAFramework-Research/src/tests/ml/test_ml_inference_lambda.py
import json, time, os
import boto3, requests

LAMBDA_NAME = os.getenv("ML_LAMBDA_NAME", "QAFrameworkMLInferenceContainer")
PUSHGATEWAY = os.getenv("PUSHGATEWAY_URL", "http://54.224.224.239:9091")

def push_metric(metric_name, value, job="ml_lambda_ci_tests"):
    data = f"{metric_name} {value}\n"
    try:
        requests.post(f"{PUSHGATEWAY}/metrics/job/{job}", data=data)
    except Exception as e:
        print(f"[WARN] Failed to push metric {metric_name}: {e}")

def test_ml_inference_lambda():
    """Functional + latency test for the ML inference Lambda (validated)."""
    client = boto3.client("lambda")

    payload = {
        "Age": 55,
        "Gender": 1,
        "High_BP": 1,
        "High_Cholesterol": 1,
        "Diabetes": 0,
        "Smoking": 0,
        "Obesity": 1
    }

    print(f"[INFO] Invoking Lambda: {LAMBDA_NAME}")
    start = time.time()
    response = client.invoke(
        FunctionName=LAMBDA_NAME,
        InvocationType="RequestResponse",
        Payload=json.dumps(payload)
    )
    latency = round((time.time() - start) * 1000, 2)

    raw_payload = response["Payload"].read()
    body = json.loads(raw_payload)

    # Parse nested JSON body
    if isinstance(body, dict) and "body" in body:
        body = json.loads(body["body"])

    print("[INFO] Final Parsed Response:", body)

    # Validations
    assert "predicted_class" in body, "Missing key: predicted_class"
    assert "risk_probability" in body, "Missing key: risk_probability"
    assert 0 <= body["risk_probability"] <= 1, "Invalid probability value"

    # Push metrics
    push_metric("ml_lambda_ci_invocation_latency_ms", latency)
    push_metric("ml_lambda_ci_test_success", 1)

    print(f"[SUCCESS] ML Lambda test passed ✅  | Latency: {latency} ms")

if __name__ == "__main__":
    test_ml_inference_lambda()
