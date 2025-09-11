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

# DynamoDB table
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.getenv("TABLE_NAME", "ItemsTable"))

def lambda_handler(event, context):
    # 🔎 Log full incoming event for debugging
    logger.info("Received event: %s", json.dumps(event))
    print("=== FULL EVENT START ===")
    print(json.dumps(event))
    print("=== FULL EVENT END ===")

    # ✅ Unified parsing for API Gateway v1/v2 + test invoke
    if "requestContext" in event and "http" in event["requestContext"]:  # v2
        method = event["requestContext"]["http"].get("method")
        path = event.get("rawPath", "/")
    else:  # v1 or manual test
        method = event.get("httpMethod")
        path = event.get("path", "/")

    cors_headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type,Authorization"
    }

    # Handle preflight
    if method == "OPTIONS":
        return {"statusCode": 200, "headers": cors_headers, "body": ""}

    # Root route
    if path in ["", "/", f"/{STAGE}", f"/{STAGE}/"]:
        return {
            "statusCode": 200,
            "headers": {**cors_headers, "Content-Type": "application/json"},
            "body": '{"message": "Hello from Lambda CRUD API!"}'
        }

    # CRUD routes
    try:
        if path == f"/{STAGE}/items" and method == "POST":
            body = json.loads(event["body"])
            table.put_item(Item=body)
            return {"statusCode": 200, "headers": cors_headers, "body": json.dumps({"message": "Item created", "item": body})}

        elif path == f"/{STAGE}/items" and method == "GET":
            item_id = event["queryStringParameters"]["id"]
            response = table.get_item(Key={"id": item_id})
            return {"statusCode": 200, "headers": cors_headers, "body": json.dumps(response.get("Item", {}))}

        elif path == f"/{STAGE}/items" and method == "PUT":
            body = json.loads(event["body"])
            table.put_item(Item=body)  # overwrite
            return {"statusCode": 200, "headers": cors_headers, "body": json.dumps({"message": "Item updated", "item": body})}

        elif path == f"/{STAGE}/items" and method == "DELETE":
            item_id = event["queryStringParameters"]["id"]
            table.delete_item(Key={"id": item_id})
            return {"statusCode": 200, "headers": cors_headers, "body": json.dumps({"message": f"Item {item_id} deleted"})}

        else:
            return {"statusCode": 404, "headers": cors_headers, "body": '{"error": "Not Found"}'}

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return {"statusCode": 500, "headers": cors_headers, "body": json.dumps({"error": str(e)})}
