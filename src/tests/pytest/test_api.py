import pytest
import requests
import time
from src.utils.config import API_ENDPOINTS    # ✅ import from config

@pytest.fixture
def base_url():
    """Fixture for base URL of the Lambda API"""
    return API_ENDPOINTS["health_check"]  # ✅ now taken from config.py


@pytest.fixture
def capture_response(request):
    """Fixture to capture response details and attach to report"""
    def _capture(response):
        request.node.funcargs["response_data"] = {
            "status_code": response.status_code,
            "body": response.text,
            "headers": dict(response.headers),
            "elapsed_time": response.elapsed.total_seconds()
        }
        return response
    return _capture


# 1. Positive flow
def test_lambda_returns_expected_message(base_url, capture_response):
    response = capture_response(requests.get(base_url))
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert data["message"] == "Hello from Lambda v2 - CD test!"


# 2. Negative flow
def test_invalid_path_returns_404(base_url, capture_response):
    response = capture_response(requests.get(f"{base_url}/wrong-endpoint"))
    assert response.status_code == 404


# 3. Performance baseline
def test_lambda_response_time(base_url, capture_response):
    start = time.time()
    response = capture_response(requests.get(base_url))
    duration = time.time() - start
    assert response.status_code == 200
    assert duration < 2.0, f"Response too slow: {duration:.3f}s"


# 3a. Cold start latency
def test_lambda_response_time_cold(base_url, capture_response):
    start = time.time()
    response = capture_response(requests.get(base_url))
    duration = time.time() - start
    assert response.status_code == 200
    assert duration < 2.5, f"Cold start too slow: {duration:.3f}s"


# 3b. Warm start latency
def test_lambda_response_time_warm(base_url, capture_response):
    requests.get(base_url)  # warmup
    start = time.time()
    response = capture_response(requests.get(base_url))
    duration = time.time() - start
    assert response.status_code == 200
    assert duration < 2.0, f"Warm start too slow: {duration:.3f}s"


# 4. Security headers
def test_lambda_security_headers(base_url, capture_response):
    response = capture_response(requests.options(base_url))
    assert response.status_code in [200, 204]

    headers = {k.lower(): v for k, v in response.headers.items()}

    if "access-control-allow-origin" in headers:
        assert headers["access-control-allow-origin"] == "*"
    else:
        pytest.skip("CORS headers not returned by API Gateway OPTIONS")


# 5. Idempotency
def test_lambda_idempotency(base_url, capture_response):
    first = capture_response(requests.get(base_url)).json()
    second = capture_response(requests.get(base_url)).json()
    assert first == second

# ------------------------------
# CRUD API Tests
# ------------------------------

def test_create_item(capture_response):
    url = "https://hp0emdwj90.execute-api.us-east-1.amazonaws.com/dev/items"
    payload = {"id": "pytest123", "name": "Test Item"}
    response = capture_response(requests.post(url, json=payload))
    assert response.status_code == 200
    body = response.json()
    assert body["item"]["id"] == "pytest123"
    assert body["item"]["name"] == "Test Item"


def test_get_item(capture_response):
    url = "https://hp0emdwj90.execute-api.us-east-1.amazonaws.com/dev/items?id=pytest123"
    response = capture_response(requests.get(url))
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "pytest123"
    assert body["name"] == "Test Item"


def test_update_item(capture_response):
    url = "https://hp0emdwj90.execute-api.us-east-1.amazonaws.com/dev/items"
    payload = {"id": "pytest123", "name": "Updated Item"}
    response = capture_response(requests.put(url, json=payload))
    assert response.status_code == 200
    body = response.json()
    assert body["item"]["name"] == "Updated Item"


def test_delete_item(capture_response):
    url = "https://hp0emdwj90.execute-api.us-east-1.amazonaws.com/dev/items?id=pytest123"
    response = capture_response(requests.delete(url))
    assert response.status_code == 200
    body = response.json()
    assert "deleted" in body["message"].lower()
