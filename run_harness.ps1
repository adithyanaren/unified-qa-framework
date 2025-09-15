param (
    [string]$FunctionName = "QAFrameworkCRUD",
    [string]$Stage = "dev"
)

Write-Host "=== QAFramework Harness ==="
Write-Host "Target Lambda: $FunctionName (Stage=$Stage)"

# Timestamps for CloudWatch queries
$start = (Get-Date).ToUniversalTime().AddMinutes(-30).ToString("yyyy-MM-ddTHH:mm:ssZ")
$end   = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")

# ---- CRUD INVOCATIONS ----
$events = @(
    "event_root.json",
    "event_create.json",
    "event_read.json",
    "event_update.json",
    "event_delete.json"
)

foreach ($event in $events) {
    Write-Host "`n--- Invoking $event ---"
    aws lambda invoke `
      --function-name $FunctionName `
      --cli-binary-format raw-in-base64-out `
      --payload file://$event `
      response.json | Out-Null

    Get-Content response.json
    Start-Sleep -Seconds 2
}

# ---- CLOUDWATCH METRICS ----
Write-Host "`n=== CloudWatch Metrics ==="

# RequestsProcessed
$requestsRaw = aws cloudwatch get-metric-statistics `
  --namespace "QAFramework/Serverless" `
  --metric-name "RequestsProcessed" `
  --dimensions Name=FunctionName,Value=$FunctionName Name=Stage,Value=$Stage `
  --start-time $start `
  --end-time $end `
  --period 60 `
  --statistics Sum

Write-Host "`nRequestsProcessed:"
$requestsRaw | Out-File metrics_requests.json -Encoding utf8
Get-Content metrics_requests.json

# Export to CSV
($requestsRaw | ConvertFrom-Json).Datapoints |
    Select-Object Timestamp,Sum,Unit |
    Export-Csv -Path requests_metrics.csv -NoTypeInformation

# ColdStartCount
$coldRaw = aws cloudwatch get-metric-statistics `
  --namespace "QAFramework/Serverless" `
  --metric-name "ColdStartCount" `
  --dimensions Name=FunctionName,Value=$FunctionName Name=Stage,Value=$Stage `
  --start-time $start `
  --end-time $end `
  --period 60 `
  --statistics Sum

Write-Host "`nColdStartCount:"
$coldRaw | Out-File metrics_cold.json -Encoding utf8
Get-Content metrics_cold.json

# Export to CSV
($coldRaw | ConvertFrom-Json).Datapoints |
    Select-Object Timestamp,Sum,Unit |
    Export-Csv -Path coldstart_metrics.csv -NoTypeInformation
