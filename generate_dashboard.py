import os
import xml.etree.ElementTree as ET
import pandas as pd
import json
from jinja2 import Environment, FileSystemLoader
import plotly.express as px

# Paths
pytest_xml = "reports/pytest/results.xml"
robot_report = "reports/robot/report.html"
robot_log = "reports/robot/log.html"
robot_output = "reports/robot/output.xml"
locust_csv = "reports/locust/results_stats.csv"
cw_json = "reports/cloudwatch/coldstart.json"

# Data containers
pytest_summary = {}
robot_summary = {}
robot_details = []
locust_summary = {}
coldstart_summary = {}
robot_chart_html = ""
locust_chart_html = ""

# Parse PyTest XML (more robust for different formats)
if os.path.exists(pytest_xml):
    try:
        tree = ET.parse(pytest_xml)
        root = tree.getroot()
        pytest_summary = {
            "tests": root.attrib.get("tests", root.attrib.get("testsuite", "?")),
            "failures": root.attrib.get("failures", "?"),
            "errors": root.attrib.get("errors", "?"),
            "skipped": root.attrib.get("skipped", "?"),
        }
    except Exception as e:
        pytest_summary = {"error": f"Could not parse XML: {e}"}

# Parse Robot XML for inline embedding
if os.path.exists(robot_output):
    try:
        tree = ET.parse(robot_output)
        root = tree.getroot()

        # First suite element
        suite = root.find(".//suite")

        # Summary stats
        stat_el = suite.find("statistics/total/stat")
        if stat_el is not None:
            robot_summary = {
                "total": stat_el.attrib.get("total", "?"),
                "pass": stat_el.attrib.get("pass", "?"),
                "fail": stat_el.attrib.get("fail", "?")
            }

        # Collect test case details
        for test in suite.findall(".//test"):
            status_el = test.find("status")
            robot_details.append({
                "name": test.attrib.get("name", "Unknown"),
                "status": status_el.attrib.get("status", "?") if status_el is not None else "?",
                "message": (status_el.text or "").strip() if status_el is not None else ""
            })

        # Create Robot pass/fail pie chart
        if robot_summary and "pass" in robot_summary and "fail" in robot_summary:
            df_robot = pd.DataFrame({
                "Result": ["PASS", "FAIL"],
                "Count": [int(robot_summary["pass"]), int(robot_summary["fail"])]
            })
            fig_robot = px.pie(df_robot, names="Result", values="Count", title="Robot - Pass vs Fail")
            robot_chart_html = fig_robot.to_html(full_html=False)

    except Exception as e:
        robot_summary = {"error": f"Could not parse Robot XML: {e}"}

# Parse Locust CSV with auto column detection
if os.path.exists(locust_csv):
    df = pd.read_csv(locust_csv)

    col_requests = next((c for c in df.columns if "request" in c.lower() and "#" in c.lower()), None)
    col_failures = next((c for c in df.columns if "failure" in c.lower()), None)
    col_avg_time = next((c for c in df.columns if "average response" in c.lower()), None)

    if col_requests and col_failures and col_avg_time:
        locust_summary = {
            "requests": int(df[col_requests].sum()),
            "failures": int(df[col_failures].sum()),
            "avg_response_time": float(df[col_avg_time].mean())
        }
    else:
        locust_summary = {"error": f"Unexpected CSV columns: {list(df.columns)}"}

    # Build Locust charts
    if col_avg_time and "Name" in df.columns:
        fig = px.bar(df, x="Name", y=col_avg_time, title="Locust - Avg Response Time per Endpoint")
        locust_chart_html = fig.to_html(full_html=False)

    if "Failure Count" in df.columns and "Name" in df.columns:
        fig2 = px.bar(df, x="Name", y="Failure Count", title="Locust - Failures per Endpoint")
        locust_chart_html += fig2.to_html(full_html=False)

# Parse CloudWatch JSON
if os.path.exists(cw_json):
    with open(cw_json) as f:
        data = json.load(f)
    if data.get("Datapoints"):
        coldstart_summary = data["Datapoints"][0]

# Load Jinja2 template
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
            {% endif %}

            <h3>Embedded Report</h3>
            <iframe src="{{ robot }}"></iframe>
            <h3>Embedded Log</h3>
            <iframe src="{{ robot_log }}"></iframe>
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
    robot=robot_report if os.path.exists(robot_report) else None,
    robot_log=robot_log if os.path.exists(robot_log) else None,
    locust=locust_summary,
    locust_chart=locust_chart_html,
    coldstart=coldstart_summary,
    robot_summary=robot_summary,
    robot_details=robot_details,
    robot_chart=robot_chart_html
)

os.makedirs("reports", exist_ok=True)
with open("reports/dashboard.html", "w", encoding="utf-8") as f:
    f.write(html_out)

print("✅ Dashboard generated at reports/dashboard.html")
