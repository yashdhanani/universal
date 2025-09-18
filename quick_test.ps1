# Quick Performance Test
Write-Host "🚀 TESTING OPTIMIZED PERFORMANCE" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Green

$testUrl = "https://youtu.be/BaW_jenozKc"
$apiUrl = "http://127.0.0.1:8000"

Write-Host ""
Write-Host "🔍 Testing analysis speed..." -ForegroundColor Cyan
$startTime = Get-Date

try {
    $body = @{ url = $testUrl } | ConvertTo-Json
    $response = Invoke-RestMethod -Uri "$apiUrl/api/youtube/analyze" -Method POST -Body $body -ContentType "application/json" -TimeoutSec 30
    
    $endTime = Get-Date
    $duration = ($endTime - $startTime).TotalSeconds
    
    Write-Host "✅ Analysis completed in $([math]::Round($duration, 2)) seconds" -ForegroundColor Green
    Write-Host "📊 Found $($response.mp4.Count) video formats" -ForegroundColor White
    Write-Host "📊 Found $($response.mp3.Count) audio formats" -ForegroundColor White
    
    if ($duration -lt 5) {
        Write-Host "🚀 EXCELLENT! Analysis is very fast" -ForegroundColor Green
    } elseif ($duration -lt 10) {
        Write-Host "✅ GOOD! Analysis speed is optimized" -ForegroundColor Yellow
    } else {
        Write-Host "⚠️  Analysis could be faster - check network connection" -ForegroundColor Yellow
    }
    
} catch {
    Write-Host "❌ Test failed: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Make sure the server is running on port 8000" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "🌐 Your optimized app: $apiUrl/universal_tailwind" -ForegroundColor Cyan