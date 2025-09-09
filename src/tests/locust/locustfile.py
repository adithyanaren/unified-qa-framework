from locust import HttpUser, task, between, events
from prometheus_client import start_http_server, Counter, Histogram

# Define Prometheus metrics
REQUEST_COUNT = Counter(
    "locust_requests_total",
    "Total number of requests",
    ["method", "endpoint", "status"]
)

REQUEST_LATENCY = Histogram(
    "locust_request_latency_seconds",
    "Request latency",
    ["method", "endpoint"]
)

# Start Prometheus metrics server on port 9646
start_http_server(9646)

# Hook Locust events to update metrics
@events.request.add_listener
def track_request(request_type, name, response_time, response_length, exception, **kwargs):
    status = "ok" if exception is None else "fail"
    REQUEST_COUNT.labels(request_type, name, status).inc()
    REQUEST_LATENCY.labels(request_type, name).observe(response_time / 1000.0)  # ms → seconds


class HelloLambdaUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def call_api(self):
        response = self.client.get("/")
        if response.status_code == 200:
            print("Success:", response.json())
        else:
            print("Failed with status:", response.status_code)

    @task
    def call_invalid_api(self):
        self.client.get("/this-does-not-exist")


