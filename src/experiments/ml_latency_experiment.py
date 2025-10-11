import json, os, time, statistics, boto3, requests

LAMBDA_NAME = os.getenv("ML_LAMBDA_NAME", "QAFrameworkMLInferenceContainer")
PUSHGATEWAY = os.getenv("PUSHGATEWAY_URL", "http://54.224.224.239:9091")

def push_metric(metric_name, value, job="ml_latency_experiment"):
    """Push a metric to Prometheus Pushgateway"""
    data = f"{metric_name} {value}\n"
    try:
        requests.post(f"{PUSHGATEWAY}/metrics/job/{job}", data=data, timeout=3)
    except Exception as e:
        print(f"[WARN] Push failed: {e}")

def run_experiment(num_invocations=10):
    client = boto3.client("lambda")
    latencies = []

    payload = {
        "Age": 55, "Gender": 1, "High_BP": 1,
        "High_Cholesterol": 1, "Diabetes": 0,
        "Smoking": 0, "Obesity": 1
    }

    print(f"🚀 Starting ML Lambda latency experiment ({num_invocations} invocations)")
    for i in range(num_invocations):
        start = time.time()
        response = client.invoke(
            FunctionName=LAMBDA_NAME,
            InvocationType="RequestResponse",
            Payload=json.dumps(payload)
        )
        latency = round((time.time() - start) * 1000, 2)
        latencies.append(latency)

        print(f"[{i+1}/{num_invocations}] Latency: {latency} ms")
        time.sleep(1)  # small gap between calls

    avg_latency = round(statistics.mean(latencies), 2)
    max_latency = max(latencies)
    min_latency = min(latencies)

    print(f"\n✅ Experiment complete")
    print(f"Average Latency: {avg_latency} ms | Min: {min_latency} ms | Max: {max_latency} ms")

    # Push metrics to Prometheus
    push_metric("ml_latency_avg_ms", avg_latency)
    push_metric("ml_latency_max_ms", max_latency)
    push_metric("ml_latency_min_ms", min_latency)
    push_metric("ml_latency_invocations_total", num_invocations)

if __name__ == "__main__":
    run_experiment(num_invocations=10)
