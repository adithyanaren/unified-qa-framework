import json
import logging
import boto3
import os
import time  # added for explicit timestamps

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# -------------------------------
# AWS Clients
# -------------------------------
cloudwatch = boto3.client("cloudwatch")
dynamodb = boto3.resource("dynamodb")

# -------------------------------
# Config
# -------------------------------
NAMESPACE = "QAFramework/Serverless"
STAGE = os.getenv("STAGE", "dev")
TABLE_NAME = os.getenv("TABLE_NAME", "ItemsTable")
table = dynamodb.Table(TABLE_NAME)

# -------------------------------
# Cold start detection
# -------------------------------
IS_COLD_START = True


def publish_metrics(function_name, is_cold_start):
    """Publish CloudWatch metrics for RequestsProcessed and ColdStartCount."""
    try:
        metric_data = [
            {
                "MetricName": "RequestsProcessed",
                "Dimensions": [
                    {"Name": "FunctionName", "Value": function_name},
                    {"Name": "Stage", "Value": STAGE},
                ],
                "Timestamp": time.time(),  # ensure timestamp included
                "Value": 1,
                "Unit": "Count",
            }
        ]

        if is_cold_start:
            metric_data.append(
                {
                    "MetricName": "ColdStartCount",
                    "Dimensions": [
                        {"Name": "FunctionName", "Value": function_name},
                        {"Name": "Stage", "Value": STAGE},
                    ],
                    "Timestamp": time.time(),
                    "Value": 1,
                    "Unit": "Count",
                }
            )

        response = cloudwatch.put_metric_data(
            Namespace=NAMESPACE, MetricData=metric_data
        )
        # Log both the request and AWS' response
        logger.info(f"✅ Published metrics: {metric_data}")
        logger.info(f"📊 CloudWatch put_metric_data response: {response}")

    except Exception as e:
        logger.error(f"❌ Failed to publish metrics: {e}")


def lambda_handler(event, context):
    global IS_COLD_START
    logger.info("Received event: %s", json.dumps(event))

    function_name = context.function_name if context else "UnknownFunction"

    # Publish metrics (batch)
    publish_metrics(function_name, IS_COLD_START)
    IS_COLD_START = False

    # Extract method and path
    if "requestContext" in event and "http" in event["requestContext"]:  # HTTP API v2
        method = event["requestContext"]["http"].get("method")
        path = event.get("rawPath", "/")
    else:  # REST API v1 or direct invoke
        method = event.get("httpMethod")
        path = event.get("path", "/")

    # Common headers
    cors_headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type,Authorization",
    }

    if method == "OPTIONS":
        return {"statusCode": 200, "headers": cors_headers, "body": ""}

    try:
        # Root endpoint
        if path in ["", "/", f"/{STAGE}", f"/{STAGE}/"]:
            return {
                "statusCode": 200,
                "headers": {**cors_headers, "Content-Type": "application/json"},
                "body": json.dumps({"message": "Hello from Lambda CRUD API!"}),
            }

        # POST /items
        elif path == f"/{STAGE}/items" and method == "POST":
            body = json.loads(event.get("body", "{}"))
            if "id" not in body:
                return {
                    "statusCode": 400,
                    "headers": cors_headers,
                    "body": json.dumps({"error": "Missing 'id' in request body"}),
                }
            table.put_item(Item=body)
            return {
                "statusCode": 200,
                "headers": cors_headers,
                "body": json.dumps({"message": "Item created", "item": body}),
            }

        # GET /items?id=123
        elif path == f"/{STAGE}/items" and method == "GET":
            params = event.get("queryStringParameters") or {}
            item_id = params.get("id")
            if not item_id:
                return {
                    "statusCode": 400,
                    "headers": cors_headers,
                    "body": json.dumps({"error": "Missing 'id' parameter"}),
                }
            response = table.get_item(Key={"id": item_id})
            return {
                "statusCode": 200,
                "headers": cors_headers,
                "body": json.dumps(response.get("Item", {})),
            }

        # PUT /items
        elif path == f"/{STAGE}/items" and method == "PUT":
            body = json.loads(event.get("body", "{}"))
            if "id" not in body:
                return {
                    "statusCode": 400,
                    "headers": cors_headers,
                    "body": json.dumps({"error": "Missing 'id' in request body"}),
                }
            table.put_item(Item=body)
            return {
                "statusCode": 200,
                "headers": cors_headers,
                "body": json.dumps({"message": "Item updated", "item": body}),
            }

        # DELETE /items?id=123
        elif path == f"/{STAGE}/items" and method == "DELETE":
            params = event.get("queryStringParameters") or {}
            item_id = params.get("id")
            if not item_id:
                return {
                    "statusCode": 400,
                    "headers": cors_headers,
                    "body": json.dumps({"error": "Missing 'id' parameter"}),
                }
            table.delete_item(Key={"id": item_id})
            return {
                "statusCode": 200,
                "headers": cors_headers,
                "body": json.dumps({"message": f"Item {item_id} deleted"}),
            }

        else:
            return {
                "statusCode": 404,
                "headers": cors_headers,
                "body": json.dumps({"error": "Not Found"}),
            }

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return {
            "statusCode": 500,
            "headers": cors_headers,
            "body": json.dumps({"error": str(e)}),
        }
