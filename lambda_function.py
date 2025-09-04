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
    path = event.get("rawPath", "/")

    cors_headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type,Authorization"
    }

    # Handle preflight request (OPTIONS)
    if event.get("requestContext", {}).get("http", {}).get("method") == "OPTIONS":
        return {
            "statusCode": 200,
            "headers": cors_headers,
            "body": ""
        }

    # Main route: handle both "" and "/" paths
    if path in ["", "/", "/dev", "/dev/"]:
        return {
            "statusCode": 200,
            "headers": {**cors_headers, "Content-Type": "application/json"},
            "body": '{"message": "Hello from your first Lambda!"}'
        }
    else:
        return {
            "statusCode": 404,
            "headers": {**cors_headers, "Content-Type": "application/json"},
            "body": '{"error": "Not Found"}'
        }
