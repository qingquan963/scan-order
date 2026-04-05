$base = "http://127.0.0.1:8002/api/v1"

# Login
$loginResp = Invoke-WebRequest -Uri "$base/admin/auth/login" -Method POST -ContentType "application/json" -Body '{"username":"admin","password":"admin123"}' -UseBasicParsing
$token = ($loginResp.Content | ConvertFrom-Json).access_token
Write-Host "Token obtained" -ForegroundColor Green

# Try update settings with detailed error
$headers = @{"Authorization"="Bearer $token"; "Content-Type"="application/json"}
$body = '{"mode":"counter_pay"}'
try {
    $resp = Invoke-WebRequest -Uri "$base/admin/settings" -Method PUT -Headers $headers -Body $body -UseBasicParsing
    Write-Host "Success: $($resp.StatusCode)"
    Write-Host $resp.Content
} catch {
    Write-Host "Error: $($_.Exception.Response.StatusCode)"
    $reader = [System.IO.StreamReader]::new($_.Exception.Response.GetResponseStream())
    $errResp = $reader.ReadToEnd()
    $reader.Close()
    Write-Host "Response body: $errResp"
}
