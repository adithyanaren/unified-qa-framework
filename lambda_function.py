import json
import logging
import boto3
import os

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# CloudWatch client
cloudwatch = boto3.client("cloudwatch")
NAMESPACE = "QAFramework/Serverless"
METRIC_NAME = "RequestsProcessed"
STAGE = os.getenv("STAGE", "dev")

def lambda_handler(event, context):
    logger.info("Lambda function started")
    logger.debug(f"Event received: {event}")

    # Push a custom metric (1 per invocation)
    cloudwatch.put_metric_data(
        Namespace=NAMESPACE,
        MetricData=[{
            "MetricName": METRIC_NAME,
            "Dimensions": [
                {"Name": "FunctionName", "Value": context.function_name},
                {"Name": "Stage", "Value": STAGE}
            ],
            "Unit": "Count",
            "Value": 1.0
        }]
    )

    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Hello from your first Lambda!"})
    }
