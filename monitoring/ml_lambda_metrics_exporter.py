import boto3
import requests
from datetime import datetime, timedelta

# --- CONFIG ---
FUNCTION_NAME = "QAFrameworkMLInferenceContainer"
PUSHGATEWAY_URL = "http://54.224.224.239:9091/metrics/job/ml_inference_lambda"
REGION = "us-east-1"

# --- FETCH FROM CLOUDWATCH ---
cloudwatch = boto3.client('cloudwatch', region_name=REGION)

def get_metric(metric_name, statistic):
    response = cloudwatch.get_metric_statistics(
        Namespace='AWS/Lambda',
        MetricName=metric_name,
        Dimensions=[{'Name': 'FunctionName', 'Value': FUNCTION_NAME}],
        StartTime=datetime.utcnow() - timedelta(minutes=10),
        EndTime=datetime.utcnow(),
        Period=60,
        Statistics=[statistic]
    )
    datapoints = response.get('Datapoints', [])
    return datapoints[-1][statistic] if datapoints else 0

invocations = get_metric('Invocations', 'Sum')
errors = get_metric('Errors', 'Sum')
duration = get_metric('Duration', 'Average')

# --- FORMAT FOR PROMETHEUS ---
metrics = f"""
ml_lambda_invocations_total {invocations}
ml_lambda_errors_total {errors}
ml_lambda_duration_ms {duration}
"""

# --- PUSH TO PUSHGATEWAY ---
response = requests.post(PUSHGATEWAY_URL, data=metrics.encode('utf-8'))
print("✅ Metrics pushed to Prometheus:", response.status_code)
