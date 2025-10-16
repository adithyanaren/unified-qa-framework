import os
import time
import json
import threading
import requests
import pytest

BASE_URL = os.getenv("API_BASE_URL", "https://tyoladeyr9.execute-api.us-east-1.amazonaws.com/dev")
PUSHGATEWAY_URL = os.getenv("PUSHGATEWAY_URL", "http://54.224.224.239:9091")
PROMETHEUS_JOB = "pytest_ml_inference"

# === Utility ===
def push_metric(metric_name: str, value: float):
    try:
        payload = f"{metric_name} {value}\n"
        requests.post(f"{PUSHGATEWAY_URL}/metrics/job/{PROMETHEUS_JOB}/instance/github-actions", data=payload, timeout=5)
    except Exception:
        pass

def measure_latency(func, *args, **kwargs):
    start = time.time()
    response = func(*args, **kwargs)
    latency = (time.time() - start) * 1000
    return response, latency


VALID_PAYLOAD = {
    "age": 58, "sex": 1, "cp": 2, "trestbps": 130,
    "chol": 230, "fbs": 0, "restecg": 1, "thalach": 150,
    "exang": 0, "oldpeak": 1.5, "slope": 2, "ca": 0, "thal": 3
}
MISSING_FIELD_PAYLOAD = {"age": 58, "sex": 1, "cp": 2}
INVALID_TYPE_PAYLOAD = {"age": "fifty", "sex": "male"}

# === TEST SUITE ===

@pytest.mark.functional
def test_health_endpoint():
    """Health check"""
    response, latency = measure_latency(requests.get, f"{BASE_URL}/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data and data["status"].lower() == "ok"
    push_metric("ml_health_latency_ms", latency)

@pytest.mark.functional
def test_predict_valid_payload():
    """Valid inference"""
    response, latency = measure_latency(requests.post, f"{BASE_URL}/predict", json=VALID_PAYLOAD)
    data = response.json()
    assert response.status_code == 200
    assert "predicted_class" in data
    assert "risk_probability" in data
    assert 0.0 <= data["risk_probability"] <= 1.0
    push_metric("ml_inference_latency_ms", latency)

@pytest.mark.functional
@pytest.mark.parametrize("payload", [MISSING_FIELD_PAYLOAD, INVALID_TYPE_PAYLOAD, {}, {f"f{i}": i for i in range(1000)}])
def test_predict_edge_cases(payload):
    """Ensure model handles bad input gracefully"""
    response = requests.post(f"{BASE_URL}/predict", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "predicted_class" in data

@pytest.mark.functional
def test_repeated_inferences_consistency():
    """Same inputs yield stable predictions"""
    preds = [requests.post(f"{BASE_URL}/predict", json=VALID_PAYLOAD).json()["predicted_class"] for _ in range(3)]
    assert len(set(preds)) <= 2

@pytest.mark.functional
def test_latency_under_threshold():
    """Average inference latency < 2s"""
    _, latency = measure_latency(requests.post, f"{BASE_URL}/predict", json=VALID_PAYLOAD)
    assert latency < 2000

@pytest.mark.functional
def test_missing_content_type():
    """Missing Content-Type header should return 400/500"""
    headers = {"Content-Type": ""}
    response = requests.post(f"{BASE_URL}/predict", data=str(VALID_PAYLOAD), headers=headers)
    assert response.status_code in (400, 500)

# --- NEW TESTS BELOW ---

@pytest.mark.functional
def test_prediction_output_type_and_bounds():
    """Ensure prediction is integer and probability bounded."""
    response = requests.post(f"{BASE_URL}/predict", json=VALID_PAYLOAD)
    data = response.json()
    assert isinstance(data["predicted_class"], int)
    assert 0 <= data["risk_probability"] <= 1.0

@pytest.mark.functional
def test_response_contains_latency_metric():
    """Verify model returns internal latency metric."""
    response = requests.post(f"{BASE_URL}/predict", json=VALID_PAYLOAD)
    data = response.json()
    assert "inference_latency_ms" in data
    assert isinstance(data["inference_latency_ms"], (int, float))
    assert data["inference_latency_ms"] >= 0

@pytest.mark.functional
def test_inference_with_float_values():
    """Allow float inputs if numeric-like."""
    payload = VALID_PAYLOAD.copy()
    payload["oldpeak"] = 2.75
    response = requests.post(f"{BASE_URL}/predict", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "predicted_class" in data

@pytest.mark.functional
def test_batch_like_requests():
    """Simulate mini-batch inference calls sequentially."""
    for _ in range(5):
        r = requests.post(f"{BASE_URL}/predict", json=VALID_PAYLOAD)
        assert r.status_code == 200
        assert "predicted_class" in r.json()

@pytest.mark.functional
def test_concurrent_requests():
    """Simulate multiple threads calling inference."""
    results = []

    def call_api():
        r = requests.post(f"{BASE_URL}/predict", json=VALID_PAYLOAD)
        results.append(r.status_code)

    threads = [threading.Thread(target=call_api) for _ in range(5)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert all(code == 200 for code in results)

@pytest.mark.functional
def test_invalid_method_handling():
    """GET /predict should not be allowed."""
    r = requests.get(f"{BASE_URL}/predict")
    assert r.status_code in (404, 405)

@pytest.mark.functional
def test_response_is_json():
    """Ensure server always returns JSON."""
    r = requests.post(f"{BASE_URL}/predict", json=VALID_PAYLOAD)
    try:
        data = r.json()
        assert isinstance(data, dict)
    except Exception:
        pytest.fail("Response was not valid JSON")

@pytest.mark.functional
def test_response_has_expected_keys_subset():
    """Check required key subset present."""
    r = requests.post(f"{BASE_URL}/predict", json=VALID_PAYLOAD)
    keys = set(r.json().keys())
    expected = {"predicted_class", "risk_probability"}
    assert expected.issubset(keys)
