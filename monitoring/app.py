from flask import Flask
from prometheus_flask_exporter import PrometheusMetrics
from prometheus_client import Counter, Gauge
import psutil
import threading, time

app = Flask(__name__)

# Enable default Flask metrics (HTTP request counts, latency histograms, etc.)
metrics = PrometheusMetrics(app)

# Custom counter
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP Requests')

# Custom Gauges for CPU & Memory (work cross-platform)
CPU_USAGE = Gauge("app_cpu_percent", "Application CPU usage percent")
MEM_USAGE = Gauge("app_memory_bytes", "Application memory usage in bytes")

def track_usage():
    process = psutil.Process()
    process.cpu_percent(interval=None)  # prime the counter
    while True:
        CPU_USAGE.set(process.cpu_percent(interval=1))   # stable readings
        MEM_USAGE.set(process.memory_info().rss)
        time.sleep(1)


@app.route("/")
def index():
    REQUEST_COUNT.inc()
    return "Hello, QA Framework Monitoring!"

if __name__ == "__main__":
    print("🚀 Flask app starting with psutil-based CPU & memory metrics")
    threading.Thread(target=track_usage, daemon=True).start()
    app.run(host="0.0.0.0", port=5050)
