# API Smoke Tests for Phase 2 (Fixed)

$base = "http://127.0.0.1:8002/api/v1"

function Test-Api($name, $method, $path, $expectedStatus, $bodyHash = $null, $token = $null) {
    $url = "$base$path"
    $headers = @{}
    if ($token) {
        $headers["Authorization"] = "Bearer $token"
    }
    
    $params = @{
        Uri = $url
        Method = $method
        Headers = $headers
        UseBasicParsing = $true
    }
    
    if ($bodyHash) {
        $params["Body"] = ($bodyHash | ConvertTo-Json)
        $params["ContentType"] = "application/json"
    }
    
    try {
        $resp = Invoke-WebRequest @params
        $status = $resp.StatusCode
        $content = $resp.Content
    } catch {
        $status = $_.Exception.Response.StatusCode
        $content = $_.Exception.Message
    }
    
    $ok = ($status -eq $expectedStatus)
    $icon = if ($ok) { "[PASS]" } else { "[FAIL]" }
    Write-Host "$icon $name (expected $expectedStatus, got $status)"
    if (-not $ok) { Write-Host "  Response: $content" }
    return $ok
}

Write-Host "=== Phase 2 API Smoke Tests ===" -ForegroundColor Cyan

# 1. Health check
Test-Api "Health check" "GET" "/health" 200

# 2. Login
$loginResp = Invoke-WebRequest -Uri "$base/admin/auth/login" -Method POST -ContentType "application/json" -Body '{"username":"admin","password":"admin123"}' -UseBasicParsing
$loginData = $loginResp.Content | ConvertFrom-Json
$token = $loginData.access_token
Write-Host "Token obtained: $($token.Substring(0, [Math]::Min(20, $token.Length)))..." -ForegroundColor Green

# 3. Get merchant settings (needs auth)
Test-Api "Get settings" "GET" "/admin/settings" 200 $null $token

# 4. Update payment mode to counter_pay
Test-Api "Update to counter_pay" "PUT" "/admin/settings" 200 @{mode="counter_pay"} $token

# 5. Get tables
$tablesResp = Invoke-WebRequest -Uri "$base/admin/tables" -Method GET -Headers @{"Authorization"="Bearer $token"} -UseBasicParsing
$tables = $tablesResp.Content | ConvertFrom-Json
$tableId = $tables[0].id
Write-Host "Table ID: $tableId" -ForegroundColor Green

# 6. Get table QR code (binary PNG)
$qrResp = Invoke-WebRequest -Uri "$base/admin/tables/$tableId/qrcode" -Method GET -Headers @{"Authorization"="Bearer $token"} -UseBasicParsing
$isPng = $qrResp.Content.Length -gt 10 -and $qrResp.Content[0] -eq 137
$qrIcon = if ($isPng) { "PASS" } else { "FAIL" }
Write-Host "[$qrIcon] Table QR code is PNG (bytes: $($qrResp.Content.Length))"

# 7. Customer categories (public)
Test-Api "Customer categories" "GET" "/customer/categories" 200

# 8. Customer dishes (public)
Test-Api "Customer dishes" "GET" "/customer/dishes" 200

# 9. Create order in counter_pay mode -> should get pending_payment + payment_token
$orderBody = @{
    table_id = $tableId
    items = @(@{dish_id = 1; quantity = 1})
}
$orderResp = Invoke-WebRequest -Uri "$base/customer/orders" -Method POST -ContentType "application/json" -Body ($orderBody | ConvertTo-Json) -UseBasicParsing
$orderData = $orderResp.Content | ConvertFrom-Json
Write-Host "Order created: id=$($orderData.id), status=$($orderData.status), has_payment_token=$($null -ne $orderData.payment_token)" -ForegroundColor Yellow
$orderId = $orderData.id

# 10. Get order (customer) - should show pending_payment + payment_code
Test-Api "Get customer order" "GET" "/customer/orders/$orderId" 200
$orderDetail = (Invoke-WebRequest -Uri "$base/customer/orders/$orderId" -UseBasicParsing).Content | ConvertFrom-Json
Write-Host "  Order detail: status=$($orderDetail.status), payment_code=$($orderDetail.payment_code)" -ForegroundColor Gray

# 11. Confirm payment
Test-Api "Confirm payment" "POST" "/customer/orders/$orderId/pay" 200

# 12. Get order after payment - should be pending
$orderAfter = (Invoke-WebRequest -Uri "$base/customer/orders/$orderId" -UseBasicParsing).Content | ConvertFrom-Json
Write-Host "  Order after pay: status=$($orderAfter.status)" -ForegroundColor Yellow

# 13. Create order in credit_pay mode (change mode first)
Test-Api "Update to credit_pay" "PUT" "/admin/settings" 200 @{mode="credit_pay"} $token
$order2Resp = Invoke-WebRequest -Uri "$base/customer/orders" -Method POST -ContentType "application/json" -Body ($orderBody | ConvertTo-Json) -UseBasicParsing
$order2Data = $order2Resp.Content | ConvertFrom-Json
Write-Host "Order2 created: id=$($order2Data.id), status=$($order2Data.status), has_payment_token=$($null -ne $order2Data.payment_token)" -ForegroundColor Yellow

# 14. Admin orders list (should include payment_mode, paid_at)
Test-Api "Admin orders list" "GET" "/admin/orders" 200 $null $token
$adminOrders = (Invoke-WebRequest -Uri "$base/admin/orders" -Method GET -Headers @{"Authorization"="Bearer $token"} -UseBasicParsing).Content | ConvertFrom-Json
Write-Host "  Admin orders: total=$($adminOrders.total), first order has payment_mode=$($adminOrders.orders[0].payment_mode)" -ForegroundColor Gray

# 15. Public merchant settings (no auth)
Test-Api "Public merchant settings" "GET" "/customer/merchants/1/settings" 200

# 16. Admin get order detail
$adminOrderResp = Invoke-WebRequest -Uri "$base/admin/orders/$orderId" -Method GET -Headers @{"Authorization"="Bearer $token"} -UseBasicParsing
$adminOrderDetail = $adminOrderResp.Content | ConvertFrom-Json
Write-Host "  Admin order detail: payment_mode=$($adminOrderDetail.payment_mode), paid_at=$($adminOrderDetail.paid_at)" -ForegroundColor Gray

# 17. Invalid payment mode update
Test-Api "Invalid mode reject" "PUT" "/admin/settings" 400 @{mode="invalid_mode"} $token

Write-Host ""
Write-Host "=== All Tests Complete ===" -ForegroundColor Cyan
