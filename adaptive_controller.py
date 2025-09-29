import boto3
import requests
import subprocess
import datetime
import os

# Config
REGION = "us-east-1"
NAMESPACE = "QAFramework"
PROMETHEUS_PUSHGATEWAY = os.getenv("PUSHGATEWAY_URL", "http://localhost:9091")
COLDSTART_THRESHOLD = 2
REQUEST_THRESHOLD = 1

cloudwatch = boto3.client("cloudwatch", region_name=REGION)


def fetch_cloudwatch_metric(metric_name, period=60):
    now = datetime.datetime.utcnow()
    start = now - datetime.timedelta(minutes=5)

    response = cloudwatch.get_metric_statistics(
        Namespace=NAMESPACE,
        MetricName=metric_name,
        StartTime=start,
        EndTime=now,
        Period=period,
        Statistics=["Sum"]
    )
    datapoints = response.get("Datapoints", [])
    if not datapoints:
        return 0
    return int(datapoints[-1]["Sum"])


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
    requests_processed = fetch_cloudwatch_metric("RequestsProcessed")
    cold_starts = fetch_cloudwatch_metric("ColdStartCount")

    print(f"[Controller] RequestsProcessed={requests_processed}, ColdStarts={cold_starts}")

    push_to_prometheus("qa_requests_processed", requests_processed)
    push_to_prometheus("qa_cold_starts", cold_starts)

    if cold_starts > COLDSTART_THRESHOLD:
        trigger_tests("locust")
    if requests_processed < REQUEST_THRESHOLD:
        trigger_tests("robot")


if __name__ == "__main__":
    main()
