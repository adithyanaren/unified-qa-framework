import os
import xml.etree.ElementTree as ET
import pandas as pd
import json
from jinja2 import Environment, FileSystemLoader
import plotly.express as px

# Paths
pytest_xml = "reports/pytest/results.xml"
robot_report = "reports/robot/report.html"
locust_csv = "reports/locust/results_stats.csv"
cw_json = "reports/cloudwatch/coldstart.json"

# Data containers
pytest_summary = {}
locust_summary = {}
coldstart_summary = {}

# Parse PyTest XML
if os.path.exists(pytest_xml):
    tree = ET.parse(pytest_xml)
    root = tree.getroot()
    pytest_summary = {
        "tests": root.attrib.get("tests", "?"),
        "failures": root.attrib.get("failures", "?"),
        "errors": root.attrib.get("errors", "?"),
        "skipped": root.attrib.get("skipped", "?"),
    }

# Parse Locust CSV
if os.path.exists(locust_csv):
    df = pd.read_csv(locust_csv)

    # Try to detect request/failure/response columns automatically
    col_requests = next((c for c in df.columns if "requests" in c.lower()), None)
    col_failures = next((c for c in df.columns if "failures" in c.lower()), None)
    col_avg_time = next((c for c in df.columns if "average response" in c.lower()), None)

    if col_requests and col_failures and col_avg_time:
        locust_summary = {
            "requests": int(df[col_requests].sum()),
            "failures": int(df[col_failures].sum()),
            "avg_response_time": float(df[col_avg_time].mean())
        }
    else:
        locust_summary = {"error": f"Unexpected CSV columns: {list(df.columns)}"}

# Parse CloudWatch JSON
if os.path.exists(cw_json):
    with open(cw_json) as f:
        data = json.load(f)
    if data.get("Datapoints"):
        coldstart_summary = data["Datapoints"][0]

# Create Plotly chart for Locust if data available
locust_chart_html = ""
if os.path.exists(locust_csv):
    fig = px.line(df, x="Name", y="Average response time", title="Locust Response Times")
    locust_chart_html = fig.to_html(full_html=False)

# Load Jinja2 template
env = Environment(loader=FileSystemLoader("."))
template = env.from_string("""
<!DOCTYPE html>
<html>
<head>
    <title>Unified QA Dashboard</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        h1, h2 { color: #2C3E50; }
        .section { margin-bottom: 40px; }
        .metric { padding: 10px; border: 1px solid #ccc; border-radius: 5px; margin: 5px 0; }
    </style>
</head>
<body>
    <h1>Unified QA Framework - Dashboard</h1>

    <div class="section">
        <h2>PyTest Results</h2>
        {% if pytest %}
            <div class="metric">Total Tests: {{ pytest.tests }}</div>
            <div class="metric">Failures: {{ pytest.failures }}</div>
            <div class="metric">Errors: {{ pytest.errors }}</div>
            <div class="metric">Skipped: {{ pytest.skipped }}</div>
        {% else %}
            <p>No PyTest results found.</p>
        {% endif %}
    </div>

    <div class="section">
        <h2>Robot Framework</h2>
        {% if robot %}
            <p><a href="{{ robot }}">Open Robot Report</a></p>
        {% else %}
            <p>No Robot report found.</p>
        {% endif %}
    </div>

    <div class="section">
        <h2>Locust Results</h2>
        {% if locust %}
            <div class="metric">Total Requests: {{ locust.requests }}</div>
            <div class="metric">Failures: {{ locust.failures }}</div>
            <div class="metric">Avg Response Time: {{ locust.avg_response_time }} ms</div>
            <div>{{ locust_chart|safe }}</div>
        {% else %}
            <p>No Locust results found.</p>
        {% endif %}
    </div>

    <div class="section">
        <h2>CloudWatch - Cold Starts</h2>
        {% if coldstart %}
            <div class="metric">ColdStartCount: {{ coldstart.Sum }}</div>
            <div class="metric">Timestamp: {{ coldstart.Timestamp }}</div>
        {% else %}
            <p>No CloudWatch metrics found.</p>
        {% endif %}
    </div>

</body>
</html>
""")

# Render HTML
html_out = template.render(
    pytest=pytest_summary,
    robot=robot_report if os.path.exists(robot_report) else None,
    locust=locust_summary,
    locust_chart=locust_chart_html,
    coldstart=coldstart_summary,
)

with open("reports/dashboard.html", "w", encoding="utf-8") as f:
    f.write(html_out)

print("✅ Dashboard generated at reports/dashboard.html")
