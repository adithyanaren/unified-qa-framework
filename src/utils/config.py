# src/utils/config.py

# ---------- AWS General ----------
AWS_REGION = "us-east-1"   # change if your Lambda is deployed elsewhere

# ---------- Lambda Functions ----------
LAMBDA_FUNCTIONS = {
    "hello_world": "my-hello-world-func",
    "heavy_task": "my-heavy-task-func"
}

# ---------- API Gateway ----------
API_ENDPOINTS = {
    "health_check": "https://prl0fjqceh.execute-api.us-east-1.amazonaws.com/dev",
    "process_data": "https://prl0fjqceh.execute-api.us-east-1.amazonaws.com/dev/process"
}


# ---------- CloudWatch ----------
LOG_GROUPS = {
    "hello_world": "/aws/lambda/my-hello-world-func",
    "heavy_task": "/aws/lambda/my-heavy-task-func"
}

# ---------- Load Testing ----------
LOCUST_SETTINGS = {
    "users": 50,
    "spawn_rate": 5,
    "run_time": "1m"  # 1 minute, format: "10s", "5m", "1h"
}

# For Robot Framework compatibility
API_URL = API_ENDPOINTS["health_check"]
