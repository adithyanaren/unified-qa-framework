from locust import HttpUser, task, between, events
from prometheus_client import start_http_server, Counter, Histogram
import uuid

# Prometheus metrics
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

start_http_server(9646)

@events.request.add_listener
def track_request(request_type, name, response_time, response_length, exception, **kwargs):
    status = "ok" if exception is None else "fail"
    REQUEST_COUNT.labels(request_type, name, status).inc()
    REQUEST_LATENCY.labels(request_type, name).observe(response_time / 1000.0)

# Read env var (default = true for local, false in CI/CD)
# NEGATIVE_TESTS = os.getenv("NEGATIVE_TESTS", "true").lower() == "true"

class CrudApiUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def call_health(self):
        self.client.get("/dev")

    # if NEGATIVE_TESTS:
    #     @task
    #     def call_invalid(self):
    #         self.client.get("/this-does-not-exist")

    @task
    def crud_cycle(self):
        # generate unique ID per test
        item_id = str(uuid.uuid4())

        # POST
        payload = {"id": item_id, "name": "Locust Item"}
        self.client.post("/dev/items", json=payload)

        # GET
        self.client.get("/dev/items", params={"id": item_id})

        # PUT
        self.client.put("/dev/items", json={"id": item_id, "name": "Updated Locust Item"})

        # DELETE
        self.client.delete("/dev/items", params={"id": item_id})

