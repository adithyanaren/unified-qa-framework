from locust import HttpUser, task, between
import random, json, time

# =====================================================
# Unified QA Framework – ML Inference Load Tests
# =====================================================
# Simulates 7 behavioral and performance scenarios for
# the ML inference Lambda API integrated with
# CloudWatch → Prometheus → Grafana.
# =====================================================

class MLInferenceUser(HttpUser):
    wait_time = between(1, 3)
    host = "https://tyoladeyr9.execute-api.us-east-1.amazonaws.com/dev"

    # -----------------------------
    # Helper: random payload
    # -----------------------------
    def generate_payload(self):
        return {
            "age": random.randint(29, 77),
            "sex": random.choice([0, 1]),
            "cp": random.randint(0, 3),
            "trestbps": random.randint(100, 180),
            "chol": random.randint(150, 350),
            "fbs": random.choice([0, 1]),
            "restecg": random.randint(0, 2),
            "thalach": random.randint(90, 200),
            "exang": random.choice([0, 1]),
            "oldpeak": round(random.uniform(0.0, 4.0), 1),
            "slope": random.randint(0, 2),
            "ca": random.randint(0, 3),
            "thal": random.randint(0, 3)
        }

    # --------------------------------------------------
    # 1. Health Check Load Test
    # --------------------------------------------------
    @task(1)
    def health_check_load(self):
        with self.client.get("/health", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Health check failed: {response.status_code}")

    # --------------------------------------------------
    # 2. Normal Inference Load Test
    # --------------------------------------------------
    @task(2)
    def normal_inference_load(self):
        payload = self.generate_payload()
        headers = {"Content-Type": "application/json"}
        with self.client.post("/predict", data=json.dumps(payload), headers=headers, catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Normal inference failed: {response.status_code}")

    # --------------------------------------------------
    # 3. High Concurrency Stress Test
    # --------------------------------------------------
    @task(1)
    def high_concurrency_stress_test(self):
        payload = self.generate_payload()
        headers = {"Content-Type": "application/json"}
        with self.client.post("/predict", data=json.dumps(payload), headers=headers, catch_response=True) as response:
            if response.status_code not in [200, 400]:
                response.failure(f"Stress test failure: {response.status_code}")

    # --------------------------------------------------
    # 4. Sustained Load Stability Test
    # --------------------------------------------------
    @task(1)
    def sustained_load_stability(self):
        payload = self.generate_payload()
        headers = {"Content-Type": "application/json"}
        start = time.time()
        with self.client.post("/predict", data=json.dumps(payload), headers=headers, catch_response=True) as response:
            duration = time.time() - start
            if duration > 2.0:
                response.failure(f"High latency detected: {duration:.2f}s")
            else:
                response.success()

    # --------------------------------------------------
    # 5. Payload Variation Test
    # --------------------------------------------------
    @task(1)
    def payload_variation_test(self):
        payload = self.generate_payload()
        payload["chol"] = random.randint(100, 400)
        payload["thalach"] = random.randint(80, 210)
        headers = {"Content-Type": "application/json"}
        self.client.post("/predict", data=json.dumps(payload), headers=headers)

    # --------------------------------------------------
    # 6. Invalid Payload Flood Test
    # --------------------------------------------------
    @task(1)
    def invalid_payload_flood(self):
        invalid_payloads = [
            {},  # empty
            {"age": 55},  # missing fields
            {"chol": "abc"},  # wrong datatype
            {"age": -10, "sex": 3, "fbs": 99},  # out of range
        ]
        headers = {"Content-Type": "application/json"}
        payload = random.choice(invalid_payloads)
        with self.client.post("/predict", data=json.dumps(payload), headers=headers, catch_response=True) as response:
            if response.status_code in [400, 422]:
                response.success()
            else:
                response.failure(f"Invalid payload not handled: {response.status_code}")

    # --------------------------------------------------
    # 7. Cold Start Observation Test
    # --------------------------------------------------
    @task(1)
    def cold_start_observation(self):
        time.sleep(5)
        payload = self.generate_payload()
        headers = {"Content-Type": "application/json"}
        with self.client.post("/predict", data=json.dumps(payload), headers=headers, catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure("Cold start failed")


# =====================================================
# Usage
# =====================================================
# Interactive UI:
#   locust -f locust_ml_inference.py
#
# Headless CI/CD mode:
#   locust -f locust_ml_inference.py --headless -u 50 -r 10 -t 2m --csv=locust_results --only-summary
#
# Prometheus Push (manual check):
#   echo "locust_avg_latency_ms $(awk -F, '/Total/ {print $9}' locust_results_stats.csv)" \
#     | curl --data-binary @- http://54.224.224.239:9091/metrics/job/locust_performance
#   echo "locust_fail_ratio $(awk -F, '/Total/ {print $7}' locust_results_stats.csv)" \
#     | curl --data-binary @- http://54.224.224.239:9091/metrics/job/locust_performance
#   echo "locust_requests_per_second $(awk -F, '/Total/ {print $8}' locust_results_stats.csv)" \
#     | curl --data-binary @- http://54.224.224.239:9091/metrics/job/locust_performance
