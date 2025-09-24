metrics = """locust_requests_total 123
locust_failures_total 4
locust_avg_latency_ms 45.6
"""

with open("locust.prom", "w", newline="\n") as f:
    f.write(metrics)
