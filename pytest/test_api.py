import requests

API_URL = "https://prl0fjqceh.execute-api.us-east-1.amazonaws.com"

def test_hello_lambda():
    response = requests.get(API_URL)
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert data["message"] == "Hello from your first Lambda!"
