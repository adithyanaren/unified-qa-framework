import requests
import subprocess
import datetime
import os
import time

# === Config ===
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://54.224.224.239:9090")  # EC2 public Prometheus
PROMETHEUS_PUSHGATEWAY = os.getenv("PUSHGATEWAY_URL", "http://54.224.224.239:9091")  # EC2 Pushgateway

COLDSTART_THRESHOLD = 2
REQUEST_THRESHOLD = 1
RETRY_DELAY = 5  # seconds

print(f"[Controller] Using Prometheus at {PROMETHEUS_URL}")
print(f"[Controller] Using Pushgateway at {PROMETHEUS_PUSHGATEWAY}")

# === Utility functions ===
def fetch_prometheus_metric(query):
    """Fetch a single metric value from Prometheus."""
    url = f"{PROMETHEUS_URL}/api/v1/query"
    try:
        response = requests.get(url, params={"query": query}, timeout=10)
        response.raise_for_status()
        result = response.json().get("data", {}).get("result", [])
        if result:
            value = int(float(result[0]["value"][1]))
            print(f"[Controller] {query} = {value}")
            return value
        else:
            print(f"[Controller] No data for {query}, returning 0.")
    except Exception as e:
        print(f"[Controller] Error fetching {query}: {e}")
    return 0


def trigger_tests(test_type):
    """Trigger functional, performance, or behavioral tests."""
    print(f"[Controller] Triggering {test_type} tests...")
    try:
        if test_type == "locust":
            # Run Locust headless against the Lambda API Gateway endpoint
            subprocess.run([
                "locust",
                "-f", "src/tests/locust/locustfile.py",
                "--headless",
                "-u", "10",              # number of users
                "-r", "2",               # spawn rate
                "-t", "1m",              # duration
                "--host", "https://hp0emdwj90.execute-api.us-east-1.amazonaws.com/dev"
            ], check=False)

        elif test_type == "robot":
            subprocess.run(["robot", "src/tests/Robot/api_tests.robot"], check=False)

        elif test_type == "pytest":
            subprocess.run(["pytest", "src/tests/pytest"], check=False)

    except Exception as e:
        print(f"[Controller] Error running {test_type} tests: {e}")



def push_to_prometheus(metric, value):
    """Push custom adaptive metrics to Prometheus via Pushgateway."""
    try:
        data = f"{metric} {value}\n"
        requests.post(f"{PROMETHEUS_PUSHGATEWAY}/metrics/job/adaptive_controller", data=data, timeout=10)
        print(f"[Controller] Pushed {metric}={value} to Pushgateway.")
    except Exception as e:
        print(f"[Controller] Failed to push {metric}: {e}")


def check_prometheus_connection():
    """Ensure Prometheus is reachable before proceeding."""
    try:
        r = requests.get(f"{PROMETHEUS_URL}/-/ready", timeout=5)
        if r.status_code == 200:
            print("[Controller] Prometheus is reachable.")
            return True
    except Exception as e:
        print(f"[Controller] Prometheus not reachable: {e}")
    return False


def main():
    if not check_prometheus_connection():
        print(f"[Controller] Retrying Prometheus connection in {RETRY_DELAY}s...")
        time.sleep(RETRY_DELAY)
        if not check_prometheus_connection():
            print("[Controller] Prometheus unreachable — skipping adaptive checks.")
            return

    requests_processed = fetch_prometheus_metric("lambda_requests_processed")
    cold_starts = fetch_prometheus_metric("lambda_cold_start_count")

    print(f"[Controller] RequestsProcessed={requests_processed}, ColdStarts={cold_starts}")

    push_to_prometheus("qa_requests_processed", requests_processed)
    push_to_prometheus("qa_cold_starts", cold_starts)

    # === Adaptive Triggers ===
    if cold_starts > COLDSTART_THRESHOLD:
        trigger_tests("locust")
    if requests_processed < REQUEST_THRESHOLD:
        trigger_tests("robot")

    # Push adaptive controller summary metrics
    push_to_prometheus("adaptive_actions_total", 1)
    push_to_prometheus("adaptive_triggered_tests", int(cold_starts > COLDSTART_THRESHOLD or requests_processed < REQUEST_THRESHOLD))


if __name__ == "__main__":
    main()
