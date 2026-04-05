# State transition verification - full flow test

$base = "http://127.0.0.1:8002/api/v1"

# Login
$loginResp = Invoke-WebRequest -Uri "$base/admin/auth/login" -Method POST -ContentType "application/json" -Body '{"username":"admin","password":"admin123"}' -UseBasicParsing
$token = ($loginResp.Content | ConvertFrom-Json).access_token
$hdr = @{"Authorization"="Bearer $token"; "Content-Type"="application/json"}

Write-Host "=== Counter Pay Flow ===" -ForegroundColor Cyan

# Ensure counter_pay mode
Invoke-WebRequest -Uri "$base/admin/settings" -Method PUT -Headers $hdr -Body '{"mode":"counter_pay"}' -UseBasicParsing | Out-Null

# Create order -> should be pending_payment
$o1 = Invoke-WebRequest -Uri "$base/customer/orders" -Method POST -ContentType "application/json" -Body (@{table_id=1; items=@(@{dish_id=1;quantity=1})} | ConvertTo-Json) -UseBasicParsing
$o1Data = $o1.Content | ConvertFrom-Json
Write-Host "1. Create order: id=$($o1Data.id) status=$($o1Data.status) (expect: pending_payment)" -ForegroundColor Yellow

# Pay for it -> should become pending
$pay1 = Invoke-WebRequest -Uri "$base/customer/orders/$($o1Data.id)/pay" -Method POST -UseBasicParsing
$o1AfterPay = (Invoke-WebRequest -Uri "$base/customer/orders/$($o1Data.id)" -UseBasicParsing).Content | ConvertFrom-Json
Write-Host "2. After pay: status=$($o1AfterPay.status) (expect: pending)" -ForegroundColor Yellow

# Admin: pending -> confirmed
$a1 = Invoke-WebRequest -Uri "$base/admin/orders/$($o1Data.id)/status" -Method PUT -Headers $hdr -Body '{"status":"confirmed"}' -UseBasicParsing
$o1AfterConfirm = (Invoke-WebRequest -Uri "$base/customer/orders/$($o1Data.id)" -UseBasicParsing).Content | ConvertFrom-Json
Write-Host "3. Admin confirms: status=$($o1AfterConfirm.status) (expect: confirmed)" -ForegroundColor Yellow

# Admin: confirmed -> paid (sets paid_at)
$a2 = Invoke-WebRequest -Uri "$base/admin/orders/$($o1Data.id)/status" -Method PUT -Headers $hdr -Body '{"status":"paid"}' -UseBasicParsing
$o1AfterPaid = (Invoke-WebRequest -Uri "$base/customer/orders/$($o1Data.id)" -UseBasicParsing).Content | ConvertFrom-Json
Write-Host "4. Admin marks paid: status=$($o1AfterPaid.status), paid_at=$($o1AfterPaid.paid_at) (expect: paid, paid_at not null)" -ForegroundColor Yellow

# Admin: paid -> cancelled (should FAIL)
$a3 = Invoke-WebRequest -Uri "$base/admin/orders/$($o1Data.id)/status" -Method PUT -Headers $hdr -Body '{"status":"cancelled"}' -UseBasicParsing
if ($a3.StatusCode -eq 400) {
    Write-Host "5. paid->cancelled BLOCKED: PASS" -ForegroundColor Green
} else {
    Write-Host "5. paid->cancelled got $($a3.StatusCode): FAIL (expect 400)" -ForegroundColor Red
}

Write-Host ""
Write-Host "=== State Transition Summary ===" -ForegroundColor Cyan
$t1 = if ($o1AfterPay.status -eq 'pending') { "PASS" } else { "FAIL" }
$t2 = if ($o1AfterConfirm.status -eq 'confirmed') { "PASS" } else { "FAIL" }
$t3 = if ($o1AfterPaid.status -eq 'paid' -and $null -ne $o1AfterPaid.paid_at) { "PASS" } else { "FAIL" }
$t4 = if ($a3.StatusCode -eq 400) { "PASS" } else { "FAIL" }
Write-Host "pending_payment -> pending (via /pay): $t1"
Write-Host "pending -> confirmed: $t2"
Write-Host "confirmed -> paid (paid_at set): $t3"
Write-Host "paid is terminal: $t4"
