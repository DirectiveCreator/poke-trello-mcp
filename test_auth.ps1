# Test script for authenticated MCP endpoint
$url = "https://your-service-name.onrender.com/mcp"  # Replace with your actual URL
$token = "0USbNEFqvtn3cWCmj4KsVwyrH598QDZh"

# Test with authentication
Write-Host "Testing with authentication..." -ForegroundColor Green
$headers = @{
    "Authorization" = "Bearer $token"
    "Content-Type" = "application/json"
}

try {
    $response = Invoke-WebRequest -Uri $url -Headers $headers -Method GET
    Write-Host "✓ Authentication successful!" -ForegroundColor Green
    Write-Host "Response: $($response.StatusCode)" -ForegroundColor Cyan
} catch {
    Write-Host "✗ Authentication failed!" -ForegroundColor Red
    Write-Host "Error: $_" -ForegroundColor Yellow
}

# Test without authentication (should fail)
Write-Host "`nTesting without authentication..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri $url -Method GET
    Write-Host "✗ SECURITY ISSUE: Endpoint accessible without auth!" -ForegroundColor Red
} catch {
    Write-Host "✓ Good! Endpoint properly secured (rejected without auth)" -ForegroundColor Green
}