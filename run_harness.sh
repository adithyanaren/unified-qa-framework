#!/usr/bin/env bash
set -euo pipefail

echo "=== QAFramework Harness ==="
FUNCTION="QAFrameworkCRUD"
STAGE="dev"

echo "Target Lambda: $FUNCTION (Stage=$STAGE)"

# Ensure reports directory exists
mkdir -p reports/cloudwatch

# Invoke events one by one
for event in event_root.json event_create.json event_read.json event_update.json event_delete.json; do
  echo
  echo "--- Invoking $event ---"
  aws lambda invoke \
    --function-name $FUNCTION \
    --cli-binary-format raw-in-base64-out \
    --payload file://$event \
    response.json > /dev/null
  cat response.json
done

# Fetch CloudWatch metrics
echo
echo "=== CloudWatch Metrics ==="

# RequestsProcessed
aws cloudwatch get-metric-statistics \
  --namespace "QAFramework/Serverless" \
  --metric-name "RequestsProcessed" \
  --dimensions Name=FunctionName,Value=$FUNCTION Name=Stage,Value=$STAGE \
  --start-time $(date -u -d '30 minutes ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 60 \
  --statistics Sum > reports/cloudwatch/requests.json

echo "RequestsProcessed:"
cat reports/cloudwatch/requests.json

# ColdStartCount
aws cloudwatch get-metric-statistics \
  --namespace "QAFramework/Serverless" \
  --metric-name "ColdStartCount" \
  --dimensions Name=FunctionName,Value=$FUNCTION Name=Stage,Value=$STAGE \
  --start-time $(date -u -d '30 minutes ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 60 \
  --statistics Sum > reports/cloudwatch/coldstart.json

echo "ColdStartCount:"
cat reports/cloudwatch/coldstart.json

echo
echo "✅ Harness run complete."
