param (
    [string]$FunctionName = "QAFrameworkCRUD",
    [string]$Stage = "dev"
)

Write-Host "=== QAFramework Harness ==="
Write-Host "Target Lambda: $FunctionName (Stage=$Stage)"

# Make sure directories exist
New-Item -ItemType Directory -Force -Path "reports\harness" | Out-Null
New-Item -ItemType Directory -Force -Path "reports\cloudwatch" | Out-Null

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
    $outFile = "reports/harness/$($event.Replace('.json','.json'))"

    aws lambda invoke `
        --function-name $FunctionName `
        --cli-binary-format raw-in-base64-out `
        --payload file://$event `
        $outFile | Out-Null

    Get-Content $outFile
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

$requestsPath = "reports/cloudwatch/requests.json"
$requestsRaw | Out-File $requestsPath -Encoding utf8
Get-Content $requestsPath

# Export to CSV
($requestsRaw | ConvertFrom-Json).Datapoints |
    Select-Object Timestamp,Sum,Unit |
    Export-Csv -Path reports/cloudwatch/requests_metrics.csv -NoTypeInformation

# ColdStartCount
$coldRaw = aws cloudwatch get-metric-statistics `
  --namespace "QAFramework/Serverless" `
  --metric-name "ColdStartCount" `
  --dimensions Name=FunctionName,Value=$FunctionName Name=Stage,Value=$Stage `
  --start-time $start `
  --end-time $end `
  --period 60 `
  --statistics Sum

$coldPath = "reports/cloudwatch/coldstart.json"
$coldRaw | Out-File $coldPath -Encoding utf8
Get-Content $coldPath

# Export to CSV
($coldRaw | ConvertFrom-Json).Datapoints |
    Select-Object Timestamp,Sum,Unit |
    Export-Csv -Path reports/cloudwatch/coldstart_metrics.csv -NoTypeInformation
