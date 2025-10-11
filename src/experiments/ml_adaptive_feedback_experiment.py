import time
import json
import requests
from prometheus_client import CollectorRegistry, Gauge, push_to_gateway
import subprocess

PUSHGATEWAY = "http://54.224.224.239:9091"
PROMETHEUS_URL = "http://54.224.224.239:9090/api/v1/query"
ADAPTIVE_CONTROLLER_SCRIPT = "src/adaptive_controller.py"

def get_metric(metric_name):
    """Fetch metric from Prometheus"""
    try:
        response = requests.get(PROMETHEUS_URL, params={"query": metric_name})
        result = response.json()["data"]["result"]
        if not result:
            return None
        return float(result[0]["value"][1])
    except Exception as e:
        print(f"[ERROR] Fetching {metric_name}: {e}")
        return None

def simulate_anomaly():
    """Push a fake high-latency anomaly to Prometheus to trigger adaptive behavior"""
    registry = CollectorRegistry()
    gauge_latency = Gauge("ml_lambda_avg_latency_ms", "Simulated ML Lambda average latency", registry=registry)
    gauge_latency.set(5000)  # Simulate latency spike
    push_to_gateway(PUSHGATEWAY, job="ml_lambda_anomaly_simulation", registry=registry)
    print("⚠️ Simulated high-latency anomaly pushed to Prometheus")

def run_adaptive_controller():
    """Run the adaptive controller logic"""
    print("🧠 Running Adaptive QA Controller...")
    result = subprocess.run(["python", ADAPTIVE_CONTROLLER_SCRIPT], capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print("[ERROR]", result.stderr)

def check_adaptive_action():
    """Check if adaptive metrics show triggered tests"""
    actions = get_metric("adaptive_actions_total")
    triggered = get_metric("adaptive_triggered_tests")
    print(f"📊 Adaptive Actions: {actions}, Triggered Tests: {triggered}")
    return actions, triggered

if __name__ == "__main__":
    print("\n🚀 Starting Adaptive Feedback Validation Experiment\n")

    # Step 1: Simulate anomaly
    simulate_anomaly()
    time.sleep(5)

    # Step 2: Run the adaptive controller logic
    run_adaptive_controller()
    time.sleep(5)

    # Step 3: Check if adaptive metrics updated
    actions, triggered = check_adaptive_action()

    if actions and triggered and triggered > 0:
        print("✅ Adaptive Controller successfully detected anomaly and triggered tests!")
    else:
        print("⚠️ No adaptive response detected — check controller thresholds or metrics.")
