# ---------- AWS General ----------
AWS_REGION = "us-east-1"

# ---------- Lambda Functions ----------
LAMBDA_FUNCTIONS = {
    "crud": "QAFrameworkCRUD"
}

# ---------- API Gateway ----------
API_ENDPOINTS = {
    "health_check": "https://hp0emdwj90.execute-api.us-east-1.amazonaws.com/dev",
    "items": "https://hp0emdwj90.execute-api.us-east-1.amazonaws.com/dev/items"
}

# ---------- CloudWatch ----------
LOG_GROUPS = {
    "crud": "/aws/lambda/QAFrameworkCRUD"
}

# ---------- Load Testing ----------
LOCUST_SETTINGS = {
    "users": 10,
    "spawn_rate": 2,
    "run_time": "1m"
}

# For Robot Framework compatibility
API_URL = API_ENDPOINTS["health_check"]
