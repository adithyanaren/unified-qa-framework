import requests
import subprocess
import datetime
import os

# Config
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://localhost:9090")
PROMETHEUS_PUSHGATEWAY = os.getenv("PUSHGATEWAY_URL", "http://localhost:9091")
COLDSTART_THRESHOLD = 2
REQUEST_THRESHOLD = 1


def fetch_prometheus_metric(query):
    url = f"{PROMETHEUS_URL}/api/v1/query"
    try:
        response = requests.get(url, params={"query": query})
        result = response.json()["data"]["result"]
        if result:
            return int(float(result[0]["value"][1]))
    except Exception as e:
        print(f"[Controller] Error fetching {query}: {e}")
    return 0


def trigger_tests(test_type):
    print(f"[Controller] Triggering {test_type} tests...")
    if test_type == "locust":
        subprocess.run(["pytest", "tests/load/locust_runner.py"], check=False)
    elif test_type == "robot":
        subprocess.run(["robot", "src/tests/Robot/api_tests.robot"], check=False)
    elif test_type == "pytest":
        subprocess.run(["pytest", "tests/functional"], check=False)


def push_to_prometheus(metric, value):
    data = f"{metric} {value}\n"
    requests.post(f"{PROMETHEUS_PUSHGATEWAY}/metrics/job/adaptive_controller", data=data)


def main():
    requests_processed = fetch_prometheus_metric("lambda_requests_processed")
    cold_starts = fetch_prometheus_metric("lambda_cold_start_count")

    print(f"[Controller] RequestsProcessed={requests_processed}, ColdStarts={cold_starts}")

    push_to_prometheus("qa_requests_processed", requests_processed)
    push_to_prometheus("qa_cold_starts", cold_starts)

    if cold_starts > COLDSTART_THRESHOLD:
        trigger_tests("locust")
    if requests_processed < REQUEST_THRESHOLD:
        trigger_tests("robot")


if __name__ == "__main__":
    main()
