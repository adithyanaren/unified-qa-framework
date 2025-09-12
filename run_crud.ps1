Write-Host "=== ROOT HEALTH CHECK ==="
aws lambda invoke `
  --function-name QAFrameworkCRUD:dev `
  --cli-binary-format raw-in-base64-out `
  --payload file://event_root.json `
  response.json | Out-Null
Get-Content response.json
Write-Host ""

Write-Host "=== CREATE ==="
aws lambda invoke `
  --function-name QAFrameworkCRUD:dev `
  --cli-binary-format raw-in-base64-out `
  --payload file://event_create.json `
  response.json | Out-Null
Get-Content response.json
Write-Host ""

Write-Host "=== READ ==="
aws lambda invoke `
  --function-name QAFrameworkCRUD:dev `
  --cli-binary-format raw-in-base64-out `
  --payload file://event_read.json `
  response.json | Out-Null
Get-Content response.json
Write-Host ""

Write-Host "=== UPDATE ==="
aws lambda invoke `
  --function-name QAFrameworkCRUD:dev `
  --cli-binary-format raw-in-base64-out `
  --payload file://event_update.json `
  response.json | Out-Null
Get-Content response.json
Write-Host ""

Write-Host "=== DELETE ==="
aws lambda invoke `
  --function-name QAFrameworkCRUD:dev `
  --cli-binary-format raw-in-base64-out `
  --payload file://event_delete.json `
  response.json | Out-Null
Get-Content response.json
Write-Host ""

Write-Host "=== CLOUDWATCH METRICS (RequestsProcessed) ==="
$start = (Get-Date).ToUniversalTime().AddMinutes(-10).ToString("yyyy-MM-ddTHH:mm:ssZ")
$end   = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")

aws cloudwatch get-metric-statistics `
  --namespace "QAFramework/Serverless" `
  --metric-name "RequestsProcessed" `
  --start-time $start `
  --end-time $end `
  --period 300 `
  --statistics Sum > metrics.json

Get-Content metrics.json
