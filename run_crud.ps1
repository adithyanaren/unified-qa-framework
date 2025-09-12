for ($i = 1; $i -le 10; $i++) {
    $randomId = Get-Random -Minimum 1000 -Maximum 9999
    Write-Host "=== ITERATION $i using ID=$randomId ==="

    # Replace RANDOM_ID with real value in temp files
    (Get-Content event_create.json) -replace 'RANDOM_ID', $randomId | Set-Content temp_create.json
    (Get-Content event_update.json) -replace 'RANDOM_ID', $randomId | Set-Content temp_update.json


    # ROOT
    aws lambda invoke `
      --function-name QAFrameworkCRUD:dev `
      --cli-binary-format raw-in-base64-out `
      --payload file://event_root.json `
      response.json | Out-Null
    Get-Content response.json

    # CREATE
    aws lambda invoke `
      --function-name QAFrameworkCRUD:dev `
      --cli-binary-format raw-in-base64-out `
      --payload file://temp_create.json `
      response.json | Out-Null
    Get-Content response.json

    # READ
    aws lambda invoke `
      --function-name QAFrameworkCRUD:dev `
      --cli-binary-format raw-in-base64-out `
      --payload file://event_read.json `
      response.json | Out-Null
    Get-Content response.json

    # UPDATE
    aws lambda invoke `
      --function-name QAFrameworkCRUD:dev `
      --cli-binary-format raw-in-base64-out `
      --payload file://temp_update.json `
      response.json | Out-Null
    Get-Content response.json

    Start-Sleep -Seconds 2

    # DELETE
    aws lambda invoke `
      --function-name QAFrameworkCRUD:dev `
      --cli-binary-format raw-in-base64-out `
      --payload file://event_delete.json `
      response.json | Out-Null
    Get-Content response.json

    Start-Sleep -Seconds 2
}

# After loop, fetch metrics
Write-Host "=== CLOUDWATCH METRICS (RequestsProcessed) ==="
$start = (Get-Date).ToUniversalTime().AddMinutes(-30).ToString("yyyy-MM-ddTHH:mm:ssZ")
$end   = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")

aws cloudwatch get-metric-statistics `
  --namespace "QAFramework/Serverless" `
  --metric-name "RequestsProcessed" `
  --start-time $start `
  --end-time $end `
  --period 300 `
  --statistics Sum > metrics.json

Get-Content metrics.json
