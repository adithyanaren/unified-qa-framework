import os
import xml.etree.ElementTree as ET
import pandas as pd
import json
from jinja2 import Environment, FileSystemLoader
import plotly.express as px
import csv
from datetime import datetime

# Paths
pytest_xml = "reports/pytest/results.xml"
robot_report = "reports/robot/report.html"
robot_log = "reports/robot/log.html"
robot_output = "reports/robot/output.xml"
locust_csv = "reports/locust/results_stats.csv"
cw_json = "reports/cloudwatch/coldstart.json"

# History files
robot_history_file = "reports/robot_history.csv"
pytest_history_file = "reports/pytest_history.csv"
locust_history_file = "reports/locust_history.csv"

# Data containers
pytest_summary = {}
robot_summary = {}
robot_details = []
locust_summary = {}
coldstart_summary = {}
robot_chart_html = ""
locust_chart_html = ""
trend_robot_html = ""
trend_pytest_html = ""
trend_locust_html = ""

# --- PyTest ---
if os.path.exists(pytest_xml):
    try:
        tree = ET.parse(pytest_xml)
        root = tree.getroot()

        # Fix: Pytest counts are inside <testsuite>
        suite = root.find("testsuite") or root
        pytest_summary = {
            "tests": suite.attrib.get("tests", "?"),
            "failures": suite.attrib.get("failures", "?"),
            "errors": suite.attrib.get("errors", "?"),
            "skipped": suite.attrib.get("skipped", "?"),
        }

        # Save to history
        run_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row = [run_time,
               pytest_summary.get("tests", 0),
               pytest_summary.get("failures", 0),
               pytest_summary.get("errors", 0),
               pytest_summary.get("skipped", 0)]

        write_header = not os.path.exists(pytest_history_file)
        with open(pytest_history_file, "a", newline="") as f:
            writer = csv.writer(f)
            if write_header:
                writer.writerow(["timestamp", "tests", "failures", "errors", "skipped"])
            writer.writerow(row)

    except Exception as e:
        pytest_summary = {"error": f"Could not parse XML: {e}"}

# Build PyTest trend
if os.path.exists(pytest_history_file):
    df_hist = pd.read_csv(pytest_history_file)
    if not df_hist.empty:
        fig = px.line(df_hist, x="timestamp", y=["failures", "errors", "skipped"], markers=True,
                      title="PyTest Trend (Failures/Errors/Skipped over time)")
        trend_pytest_html = fig.to_html(full_html=False)

# --- Robot ---
if os.path.exists(robot_output):
    try:
        tree = ET.parse(robot_output)
        root = tree.getroot()

        stat_el = root.find(".//statistics/total/stat")
        if stat_el is not None:
            robot_summary = {
                "total": stat_el.attrib.get("total", "?"),
                "pass": stat_el.attrib.get("pass", "?"),
                "fail": stat_el.attrib.get("fail", "?")
            }

        for test in root.findall(".//test"):
            status_el = test.find("status")
            robot_details.append({
                "name": test.attrib.get("name", "Unknown"),
                "status": status_el.attrib.get("status", "?") if status_el is not None else "?",
                "message": (status_el.text or "").strip() if status_el is not None else ""
            })

        if robot_summary and "pass" in robot_summary and "fail" in robot_summary:
            df_robot = pd.DataFrame({
                "Result": ["PASS", "FAIL"],
                "Count": [int(robot_summary["pass"]), int(robot_summary["fail"])]
            })
            fig_robot = px.pie(df_robot, names="Result", values="Count", title="Robot - Pass vs Fail")
            robot_chart_html = fig_robot.to_html(full_html=False)

        # Save to history
        if robot_summary:
            run_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            row = [run_time, robot_summary.get("total", 0),
                   robot_summary.get("pass", 0),
                   robot_summary.get("fail", 0)]
            write_header = not os.path.exists(robot_history_file)
            with open(robot_history_file, "a", newline="") as f:
                writer = csv.writer(f)
                if write_header:
                    writer.writerow(["timestamp", "total", "pass", "fail"])
                writer.writerow(row)

    except Exception as e:
        robot_summary = {"error": f"Could not parse Robot XML: {e}"}

# Build Robot trend
if os.path.exists(robot_history_file):
    df_hist = pd.read_csv(robot_history_file)
    if not df_hist.empty:
        fig_trend = px.line(df_hist, x="timestamp", y=["pass", "fail"], markers=True,
                            title="Robot Test Trend (Pass/Fail over time)")
        trend_robot_html = fig_trend.to_html(full_html=False)

# --- Locust ---
if os.path.exists(locust_csv):
    df = pd.read_csv(locust_csv)

    # Fix: adapt to new Locust CSV column names
    col_requests = next((c for c in df.columns if "request" in c.lower() and "count" in c.lower()), None)
    col_failures = next((c for c in df.columns if "fail" in c.lower()), None)
    col_avg_time = next((c for c in df.columns if "average response" in c.lower()), None)

    if col_requests and col_failures and col_avg_time:
        locust_summary = {
            "requests": int(df[col_requests].sum()),
            "failures": int(df[col_failures].sum()),
            "avg_response_time": float(df[col_avg_time].mean())
        }

        # Save to history
        run_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row = [run_time,
               locust_summary.get("requests", 0),
               locust_summary.get("failures", 0),
               locust_summary.get("avg_response_time", 0)]
        write_header = not os.path.exists(locust_history_file)
        with open(locust_history_file, "a", newline="") as f:
            writer = csv.writer(f)
            if write_header:
                writer.writerow(["timestamp", "requests", "failures", "avg_response_time"])
            writer.writerow(row)
    else:
        locust_summary = {"error": f"Unexpected CSV columns: {list(df.columns)}"}

    if col_avg_time and "Name" in df.columns:
        fig = px.bar(df, x="Name", y=col_avg_time, title="Locust - Avg Response Time per Endpoint")
        locust_chart_html = fig.to_html(full_html=False)

    if col_failures and "Name" in df.columns:
        fig2 = px.bar(df, x="Name", y=col_failures, title="Locust - Failures per Endpoint")
        locust_chart_html += fig2.to_html(full_html=False)

# Build Locust trend
if os.path.exists(locust_history_file):
    df_hist = pd.read_csv(locust_history_file)
    if not df_hist.empty:
        fig_trend = px.line(df_hist, x="timestamp", y=["avg_response_time", "failures"], markers=True,
                            title="Locust Trend (Avg Response Time & Failures over time)")
        trend_locust_html = fig_trend.to_html(full_html=False)

# --- CloudWatch ---
if os.path.exists(cw_json):
    with open(cw_json) as f:
        data = json.load(f)
    if data.get("Datapoints"):
        coldstart_summary = data["Datapoints"][0]

# Template
env = Environment(loader=FileSystemLoader("."))
template = env.from_string("""
<!DOCTYPE html>
<html>
<head>
    <title>Unified QA Dashboard</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f8f9fa; }
        h1 { color: #2C3E50; }
        h2 { color: #34495E; border-bottom: 2px solid #ccc; padding-bottom: 5px; }
        .section { margin-bottom: 40px; padding: 15px; background: #fff; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);}
        .metric { padding: 5px 10px; margin: 5px 0; background: #ecf0f1; border-radius: 4px; }
        iframe { width: 100%; height: 600px; border: none; }
        table { border-collapse: collapse; width: 100%; margin-top: 10px; }
        th, td { padding: 8px; border: 1px solid #ccc; text-align: left; }
    </style>
</head>
<body>
    <h1>Unified QA Framework - Dashboard</h1>

    <div class="section">
        <h2>PyTest Results</h2>
        {% if pytest %}
            {% if pytest.error %}
                <p>Error: {{ pytest.error }}</p>
            {% else %}
                <div class="metric">Total Tests: {{ pytest.tests }}</div>
                <div class="metric">Failures: {{ pytest.failures }}</div>
                <div class="metric">Errors: {{ pytest.errors }}</div>
                <div class="metric">Skipped: {{ pytest.skipped }}</div>
                <div>{{ trend_pytest|safe }}</div>
            {% endif %}
        {% else %}
            <p>No PyTest results found.</p>
        {% endif %}
    </div>

    <div class="section">
        <h2>Robot Framework</h2>
        {% if robot_summary %}
            {% if robot_summary.error %}
                <p>Error: {{ robot_summary.error }}</p>
            {% else %}
                <div class="metric">Total: {{ robot_summary.total }}</div>
                <div class="metric">Passed: {{ robot_summary.pass }}</div>
                <div class="metric">Failed: {{ robot_summary.fail }}</div>
                <div>{{ robot_chart|safe }}</div>
                <h3>Test Case Results</h3>
                <table>
                    <tr><th>Name</th><th>Status</th><th>Message</th></tr>
                    {% for t in robot_details %}
                    <tr>
                        <td>{{ t.name }}</td>
                        <td style="color: {{ 'green' if t.status == 'PASS' else 'red' }}">{{ t.status }}</td>
                        <td>{{ t.message }}</td>
                    </tr>
                    {% endfor %}
                </table>
                <h3>Trend Over Time</h3>
                <div>{{ trend_robot|safe }}</div>
                <h3>Embedded Report</h3>
                <iframe src="report.html"></iframe>
                <h3>Embedded Log</h3>
                <iframe src="log.html"></iframe>
            {% endif %}
        {% else %}
            <p>No Robot report found.</p>
        {% endif %}
    </div>

    <div class="section">
        <h2>Locust Results</h2>
        {% if locust %}
            {% if locust.error %}
                <p>{{ locust.error }}</p>
            {% else %}
                <div class="metric">Total Requests: {{ locust.requests }}</div>
                <div class="metric">Failures: {{ locust.failures }}</div>
                <div class="metric">Avg Response Time: {{ locust.avg_response_time }} ms</div>
                <div>{{ locust_chart|safe }}</div>
                <h3>Trend Over Time</h3>
                <div>{{ trend_locust|safe }}</div>
            {% endif %}
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
    locust=locust_summary,
    locust_chart=locust_chart_html,
    coldstart=coldstart_summary,
    robot_summary=robot_summary,
    robot_details=robot_details,
    robot_chart=robot_chart_html,
    trend_robot=trend_robot_html,
    trend_pytest=trend_pytest_html,
    trend_locust=trend_locust_html
)

os.makedirs("reports/robot", exist_ok=True)
with open("reports/robot/Dashboard.html", "w", encoding="utf-8") as f:
    f.write(html_out)

print("✅ Dashboard generated at reports/robot/Dashboard.html")
