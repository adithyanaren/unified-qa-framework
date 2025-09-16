import json
import logging
import boto3
import os

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# CloudWatch client
cloudwatch = boto3.client("cloudwatch")
NAMESPACE = "QAFramework/Serverless"
STAGE = os.getenv("STAGE", "dev")

# DynamoDB table
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.getenv("TABLE_NAME", "ItemsTable"))

# Cold start detection
IS_COLD_START = True


def publish_metric(metric_name, function_name):
    """Publish a custom CloudWatch metric with Stage + FunctionName dimensions."""
    try:
        cloudwatch.put_metric_data(
            Namespace=NAMESPACE,
            MetricData=[
                {
                    "MetricName": metric_name,
                    "Dimensions": [
                        {"Name": "FunctionName", "Value": function_name},
                        {"Name": "Stage", "Value": STAGE}
                    ],
                    "Value": 1,
                    "Unit": "Count"
                }
            ]
        )
        logger.info(f"Published metric {metric_name} for {function_name} stage={STAGE}")
    except Exception as e:
        logger.error(f"Failed to publish metric {metric_name}: {e}")


def lambda_handler(event, context):
    global IS_COLD_START
    logger.info("Received event: %s", json.dumps(event))

    # Get actual function name from context
    function_name = context.function_name if context else "UnknownFunction"

    # Cold start metric (fires once per container)
    if IS_COLD_START:
        publish_metric("ColdStartCount", function_name)
        IS_COLD_START = False

    # Always track requests
    publish_metric("RequestsProcessed", function_name)

    # Detect method + path
    if "requestContext" in event and "http" in event["requestContext"]:  # HTTP API v2
        method = event["requestContext"]["http"].get("method")
        path = event.get("rawPath", "/")
    else:  # REST API v1 or test
        method = event.get("httpMethod")
        path = event.get("path", "/")

    cors_headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type,Authorization"
    }

    if method == "OPTIONS":
        return {"statusCode": 200, "headers": cors_headers, "body": ""}

    try:
        # Root endpoint
        if path in ["", "/", f"/{STAGE}", f"/{STAGE}/"]:
            return {
                "statusCode": 200,
                "headers": {**cors_headers, "Content-Type": "application/json"},
                "body": '{"message": "Hello from Lambda CRUD API!"}'
            }

        # POST /items
        elif path == f"/{STAGE}/items" and method == "POST":
            body = json.loads(event["body"])
            table.put_item(Item=body)
            return {"statusCode": 200, "headers": cors_headers,
                    "body": json.dumps({"message": "Item created", "item": body})}

        # GET /items?id=123
        elif path == f"/{STAGE}/items" and method == "GET":
            item_id = event["queryStringParameters"]["id"]
            response = table.get_item(Key={"id": item_id})
            return {"statusCode": 200, "headers": cors_headers,
                    "body": json.dumps(response.get("Item", {}))}

        # PUT /items
        elif path == f"/{STAGE}/items" and method == "PUT":
            body = json.loads(event["body"])
            table.put_item(Item=body)
            return {"statusCode": 200, "headers": cors_headers,
                    "body": json.dumps({"message": "Item updated", "item": body})}

        # DELETE /items?id=123
        elif path == f"/{STAGE}/items" and method == "DELETE":
            item_id = event["queryStringParameters"]["id"]
            table.delete_item(Key={"id": item_id})
            return {"statusCode": 200, "headers": cors_headers,
                    "body": json.dumps({"message": f"Item {item_id} deleted"})}

        else:
            return {"statusCode": 404, "headers": cors_headers, "body": '{"error": "Not Found"}'}

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return {"statusCode": 500, "headers": cors_headers, "body": json.dumps({"error": str(e)})}
