# Simple Activity Check for YouTube Downloader

$AppLog = "e:\project\downloader\logs\app.log"

Write-Host "=== YOUTUBE DOWNLOADER ACTIVITY ===" -ForegroundColor Green
Write-Host ""

# Check server status
Write-Host "SERVER STATUS:" -ForegroundColor Cyan
$pythonProcesses = Get-Process -Name "python" -ErrorAction SilentlyContinue
if ($pythonProcesses) {
    Write-Host "✅ Server is RUNNING" -ForegroundColor Green
    Write-Host "🌐 Access: http://127.0.0.1:5000/universal_tailwind" -ForegroundColor White
} else {
    Write-Host "❌ Server is STOPPED" -ForegroundColor Red
}
Write-Host ""

# Show recent logs
if (Test-Path $AppLog) {
    Write-Host "RECENT ACTIVITY:" -ForegroundColor Cyan
    Write-Host "----------------" -ForegroundColor Cyan
    
    $recentLogs = Get-Content $AppLog -Tail 15
    
    foreach ($line in $recentLogs) {
        if ($line -like "*Analyze request*youtube*") {
            Write-Host "🔍 YouTube Analysis Request" -ForegroundColor Green
        } elseif ($line -like "*Analyze request*instagram*") {
            Write-Host "🔍 Instagram Analysis Request" -ForegroundColor Green
        } elseif ($line -like "*Download task*started*") {
            Write-Host "⬇️  Download Started" -ForegroundColor Magenta
        } elseif ($line -like "*finished with status=finished*") {
            Write-Host "✅ Download Completed" -ForegroundColor Blue
        } elseif ($line -like "*ERROR*") {
            Write-Host "❌ Error: $line" -ForegroundColor Red
        } else {
            Write-Host $line -ForegroundColor Gray
        }
    }
    
    Write-Host ""
    Write-Host "QUICK STATS:" -ForegroundColor Cyan
    Write-Host "------------" -ForegroundColor Cyan
    
    $allContent = Get-Content $AppLog
    $totalAnalyze = ($allContent | Where-Object { $_ -like "*Analyze request*" }).Count
    $totalDownloads = ($allContent | Where-Object { $_ -like "*Download task*started*" }).Count
    $totalCompleted = ($allContent | Where-Object { $_ -like "*finished with status=finished*" }).Count
    $totalErrors = ($allContent | Where-Object { $_ -like "*ERROR*" }).Count
    
    Write-Host "📊 Total Analyze Requests: $totalAnalyze" -ForegroundColor White
    Write-Host "📊 Total Downloads Started: $totalDownloads" -ForegroundColor White  
    Write-Host "📊 Total Downloads Completed: $totalCompleted" -ForegroundColor White
    Write-Host "📊 Total Errors: $totalErrors" -ForegroundColor White
    
} else {
    Write-Host "❌ Log file not found: $AppLog" -ForegroundColor Red
}

Write-Host ""
Write-Host "💡 Your app is running at: http://127.0.0.1:5000/universal_tailwind" -ForegroundColor Yellow