import requests
import subprocess
import os
import time

# === Config ===
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://54.224.224.239:9090")   # Prometheus on EC2
PUSHGATEWAY_URL = os.getenv("PUSHGATEWAY_URL", "http://54.224.224.239:9091") # Pushgateway on EC2

LATENCY_THRESHOLD = 1500     # ms
COLDSTART_THRESHOLD = 2      # count
RETRY_DELAY = 5              # seconds

print(f"[Adaptive-ML] Prometheus → {PROMETHEUS_URL}")
print(f"[Adaptive-ML] Pushgateway → {PUSHGATEWAY_URL}")


# === Utilities ===
def fetch_metric(query):
    """Fetch a single metric value from Prometheus."""
    try:
        resp = requests.get(f"{PROMETHEUS_URL}/api/v1/query", params={"query": query}, timeout=10)
        resp.raise_for_status()
        result = resp.json().get("data", {}).get("result", [])
        if result:
            val = float(result[0]["value"][1])
            print(f"[Adaptive-ML] {query} = {val}")
            return val
        print(f"[Adaptive-ML] No data for {query}")
    except Exception as e:
        print(f"[Adaptive-ML] Error fetching {query}: {e}")
    return 0.0


def push_metric(name, value):
    """Push controller summary metrics to Prometheus via Pushgateway."""
    try:
        data = f"{name} {value}\n"
        requests.post(f"{PUSHGATEWAY_URL}/metrics/job/adaptive_ml_controller", data=data.encode(), timeout=10)
        print(f"[Adaptive-ML] Pushed {name}={value}")
    except Exception as e:
        print(f"[Adaptive-ML] Failed to push {name}: {e}")


def trigger_tests(kind):
    """Trigger Robot or Locust tests adaptively."""
    print(f"[Adaptive-ML] Triggering {kind} tests …")
    try:
        if kind == "locust":
            subprocess.run([
                "locust", "-f", "src/tests/locust/locust_ml_inference.py",
                "--headless", "-u", "10", "-r", "2", "-t", "1m",
                "--host", "https://tyoladeyr9.execute-api.us-east-1.amazonaws.com/dev"
            ], check=False)
        elif kind == "robot":
            subprocess.run(["robot", "src/tests/Robot/ml_inference_tests.robot"], check=False)
    except Exception as e:
        print(f"[Adaptive-ML] Error running {kind} tests: {e}")


# === Main adaptive logic ===
def main():
    print("[Adaptive-ML] Starting ML Adaptive Controller …")

    # --- Fetch latest ML metrics from Prometheus ---
    inference_count = fetch_metric("ml_inference_count")
    latency_ms = fetch_metric("ml_inference_latency_ms")
    cold_starts = fetch_metric("ml_model_cold_start_count")

    print(f"[Adaptive-ML] InferenceCount={inference_count}, Latency={latency_ms} ms, ColdStarts={cold_starts}")

    # --- Push metrics to Pushgateway for Grafana tracking ---
    push_metric("ml_inference_count", inference_count)
    push_metric("ml_inference_latency_ms", latency_ms)
    push_metric("ml_model_cold_start_count", cold_starts)

    # --- Decision Logic ---
    action_triggered = False

    if cold_starts > COLDSTART_THRESHOLD:
        print("⚠️  Multiple model cold starts detected → triggering Locust performance test")
        trigger_tests("locust")
        action_triggered = True

    if latency_ms > LATENCY_THRESHOLD:
        print("⚠️  High inference latency detected → triggering Robot behavioral test")
        trigger_tests("robot")
        action_triggered = True

    # --- Push adaptive controller summary metrics ---
    push_metric("adaptive_ml_actions_total", 1)
    push_metric("adaptive_ml_triggered", int(action_triggered))

    print("[Adaptive-ML] Adaptive Controller run complete ✅")


if __name__ == "__main__":
    main()
