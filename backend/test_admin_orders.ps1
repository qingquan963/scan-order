# Admin orders API fields verification
$base = "http://127.0.0.1:8002/api/v1"
$loginResp = Invoke-WebRequest -Uri "$base/admin/auth/login" -Method POST -ContentType "application/json" -Body '{"username":"admin","password":"admin123"}' -UseBasicParsing
$token = ($loginResp.Content | ConvertFrom-Json).access_token

$resp = Invoke-WebRequest -Uri "$base/admin/orders" -Method GET -Headers @{"Authorization"="Bearer $token"} -UseBasicParsing
$data = $resp.Content | ConvertFrom-Json

Write-Host "=== Admin Orders API Fields ===" -ForegroundColor Cyan
Write-Host "Total orders: $($data.total)"
Write-Host "First order fields:"
$firstOrder = $data.orders[0]
$firstOrder.PSObject.Properties | ForEach-Object { Write-Host "  $($_.Name): $($_.Value)" }

Write-Host ""
Write-Host "=== Merchant Settings Response ===" -ForegroundColor Cyan
$settingsResp = Invoke-WebRequest -Uri "$base/admin/settings" -Method GET -Headers @{"Authorization"="Bearer $token"} -UseBasicParsing
$settingsData = $settingsResp.Content | ConvertFrom-Json
$settingsData.PSObject.Properties | ForEach-Object { Write-Host "  $($_.Name): $($_.Value)" }
