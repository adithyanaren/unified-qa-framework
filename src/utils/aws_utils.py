import boto3
import json
import time

# ---------- Lambda Utilities ----------
def invoke_lambda(function_name, payload=None, invocation_type="RequestResponse"):
    """
    Invoke an AWS Lambda function.
    :param function_name: Name of the Lambda function
    :param payload: dict payload to send
    :param invocation_type: "RequestResponse" or "Event"
    :return: response dict
    """
    client = boto3.client("lambda")
    response = client.invoke(
        FunctionName=function_name,
        InvocationType=invocation_type,
        Payload=json.dumps(payload or {})
    )
    return json.loads(response["Payload"].read())


# ---------- API Gateway Utilities ----------
def call_api(endpoint_url, method="GET", headers=None, body=None):
    """
    Call an API Gateway endpoint.
    """
    import requests
    if method == "GET":
        return requests.get(endpoint_url, headers=headers).json()
    elif method == "POST":
        return requests.post(endpoint_url, headers=headers, json=body).json()
    else:
        raise ValueError("Unsupported HTTP method")


# ---------- CloudWatch Utilities ----------
def get_lambda_logs(log_group, start_time, end_time):
    """
    Fetch logs from CloudWatch for a Lambda.
    """
    client = boto3.client("logs")
    events = client.filter_log_events(
        logGroupName=log_group,
        startTime=int(start_time * 1000),
        endTime=int(end_time * 1000),
    )
    return [event["message"] for event in events["events"]]


def get_cloudwatch_metrics(namespace, metric_name, function_name, minutes=5):
    """
    Fetch recent CloudWatch metrics for Lambda.
    """
    client = boto3.client("cloudwatch")
    end = int(time.time())
    start = end - (minutes * 60)

    response = client.get_metric_statistics(
        Namespace=namespace,
        MetricName=metric_name,
        Dimensions=[{"Name": "FunctionName", "Value": function_name}],
        StartTime=start,
        EndTime=end,
        Period=60,
        Statistics=["Average"]
    )
    return response["Datapoints"]
