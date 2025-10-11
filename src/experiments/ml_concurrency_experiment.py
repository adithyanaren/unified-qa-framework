import boto3
import json
import time
import concurrent.futures
from statistics import mean
from prometheus_client import CollectorRegistry, Gauge, push_to_gateway

# === Configuration ===
LAMBDA_NAME = "QAFrameworkMLInferenceContainer"
REGION = "us-east-1"
PUSHGATEWAY = "http://54.224.224.239:9091"

# Input payload for ML inference Lambda
payload = {
    "input_features": [58, 1, 0, 130, 230, 0, 170, 0, 2.5, 1, 2, 3, 1]
}


# === Helper to invoke Lambda ===
def invoke_lambda():
    client = boto3.client("lambda", region_name=REGION)
    start = time.time()
    response = client.invoke(
        FunctionName=LAMBDA_NAME,
        InvocationType="RequestResponse",
        Payload=json.dumps(payload)
    )
    latency = (time.time() - start) * 1000
    return latency


# === Run experiment for given concurrency ===
def run_experiment(concurrency_level):
    print(f"\n🚀 Running ML Concurrency Test with {concurrency_level} parallel invocations")
    latencies = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency_level) as executor:
        futures = [executor.submit(invoke_lambda) for _ in range(concurrency_level)]
        for f in concurrent.futures.as_completed(futures):
            latencies.append(f.result())

    avg_latency = mean(latencies)
    max_latency = max(latencies)
    min_latency = min(latencies)

    print(f"✅ Completed {concurrency_level} users | Avg: {avg_latency:.2f} ms | Min: {min_latency:.2f} | Max: {max_latency:.2f}")
    return avg_latency, min_latency, max_latency


# === Main script ===
if __name__ == "__main__":
    results = {}
    concurrency_levels = [1, 5, 10, 20]

    for level in concurrency_levels:
        avg, min_l, max_l = run_experiment(level)
        results[level] = (avg, min_l, max_l)

    registry = CollectorRegistry()

    # Create labeled Gauges (shared metric name, labeled by concurrency)
    g_avg = Gauge("ml_concurrency_avg_ms", "Average latency by concurrency level (ms)", ["concurrency"], registry=registry)
    g_min = Gauge("ml_concurrency_min_ms", "Minimum latency by concurrency level (ms)", ["concurrency"], registry=registry)
    g_max = Gauge("ml_concurrency_max_ms", "Maximum latency by concurrency level (ms)", ["concurrency"], registry=registry)

    for level, (avg, min_l, max_l) in results.items():
        g_avg.labels(concurrency=str(level)).set(avg)
        g_min.labels(concurrency=str(level)).set(min_l)
        g_max.labels(concurrency=str(level)).set(max_l)

    push_to_gateway(PUSHGATEWAY, job="ml_concurrency_experiment", registry=registry)
    print("\n📊 Results pushed to Prometheus Pushgateway successfully ✅")
