import boto3
import time
import statistics
from prometheus_client import CollectorRegistry, Gauge, push_to_gateway

# === CONFIGURATION ===
LAMBDA_NAME = "QAFrameworkMLInferenceContainer"
REGION = "us-east-1"
PUSHGATEWAY_URL = "http://54.224.224.239:9091"
JOB_NAME = "ml_coldstart_experiment"
INVOCATIONS = 5  # Number of fresh invocations to test

# === AWS CLIENTS ===
lambda_client = boto3.client('lambda', region_name=REGION)
cloudwatch = boto3.client('cloudwatch', region_name=REGION)

# === METRICS ===
registry = CollectorRegistry()
g_coldstart_latency_ms = Gauge("ml_coldstart_latency_ms", "Cold start latency per run (ms)", registry=registry)
g_coldstart_avg_ms = Gauge("ml_coldstart_avg_ms", "Average cold start latency (ms)", registry=registry)
g_coldstart_invocations = Gauge("ml_coldstart_invocations_total", "Total invocations tested", registry=registry)
g_coldstart_count = Gauge("ml_coldstart_count", "Cold start count from CloudWatch", registry=registry)

# === STEP 1: Freshly invoke Lambda multiple times ===
print(f"🚀 Starting ML Cold Start Experiment for {LAMBDA_NAME} ({INVOCATIONS} invocations)")
latencies = []

for i in range(1, INVOCATIONS + 1):
    print(f"[{i}/{INVOCATIONS}] Triggering Lambda...")
    start = time.time()
    response = lambda_client.invoke(
        FunctionName=LAMBDA_NAME,
        InvocationType='RequestResponse'
    )
    end = time.time()

    latency_ms = round((end - start) * 1000, 2)
    latencies.append(latency_ms)
    g_coldstart_latency_ms.set(latency_ms)
    push_to_gateway(PUSHGATEWAY_URL, job=JOB_NAME, registry=registry)
    print(f"   → Latency: {latency_ms} ms")

    # Wait a bit between calls to increase the chance of cold starts
    time.sleep(60)

# === STEP 2: Query CloudWatch for custom metric ===
metric_data = cloudwatch.get_metric_statistics(
    Namespace='QAFrameworkMetrics',
    MetricName='ColdStartCount',
    Dimensions=[{'Name': 'FunctionName', 'Value': LAMBDA_NAME}],
    StartTime=time.time() - 3600,
    EndTime=time.time(),
    Period=300,
    Statistics=['Sum']
)

cold_start_sum = 0
if metric_data['Datapoints']:
    cold_start_sum = metric_data['Datapoints'][-1]['Sum']

g_coldstart_count.set(cold_start_sum)
g_coldstart_invocations.set(INVOCATIONS)
g_coldstart_avg_ms.set(statistics.mean(latencies))
push_to_gateway(PUSHGATEWAY_URL, job=JOB_NAME, registry=registry)

print("\n✅ Experiment Complete")
print(f"Average Latency: {round(statistics.mean(latencies), 2)} ms")
print(f"Cold Starts Detected (CloudWatch): {cold_start_sum}")
