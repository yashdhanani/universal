# Simple Activity Monitor for YouTube Downloader

$LogsDir = "e:\project\downloader\logs"
$AppLog = Join-Path $LogsDir "app.log"

Write-Host "=== YOUTUBE DOWNLOADER - ACTIVITY LOG ===" -ForegroundColor Green
Write-Host ""

# Check server status
Write-Host "SERVER STATUS:" -ForegroundColor Cyan
$pythonProcesses = Get-Process -Name "python" -ErrorAction SilentlyContinue
if ($pythonProcesses) {
    Write-Host "✅ Server is RUNNING" -ForegroundColor Green
    Write-Host "🌐 Access at: http://127.0.0.1:5000/universal_tailwind" -ForegroundColor White
} else {
    Write-Host "❌ Server is STOPPED" -ForegroundColor Red
}
Write-Host ""

# Show recent activity
if (Test-Path $AppLog) {
    Write-Host "RECENT ACTIVITY (Last 20 entries):" -ForegroundColor Cyan
    Write-Host "-----------------------------------" -ForegroundColor Cyan
    
    $recentLogs = Get-Content $AppLog -Tail 20
    
    foreach ($line in $recentLogs) {
        if ($line -match "Analyze request.*platform=(\w+).*url=([^,\s]+)") {
            $platform = $matches[1]
            $url = $matches[2]
            Write-Host "🔍 ANALYSIS: $platform - $url" -ForegroundColor Green
        } elseif ($line -match "Download task ([\w-]+) started") {
            $taskId = $matches[1]
            Write-Host "⬇️  DOWNLOAD STARTED: $taskId" -ForegroundColor Magenta
        } elseif ($line -match "Task ([\w-]+) finished with status=(\w+)") {
            $taskId = $matches[1]
            $status = $matches[2]
            Write-Host "✅ DOWNLOAD FINISHED: $taskId ($status)" -ForegroundColor Blue
        } elseif ($line -match "ERROR") {
            Write-Host "❌ ERROR: $line" -ForegroundColor Red
        } elseif ($line -match "WARNING") {
            Write-Host "⚠️  WARNING: $line" -ForegroundColor Yellow
        } else {
            Write-Host $line -ForegroundColor Gray
        }
    }
    
    Write-Host ""
    Write-Host "STATISTICS:" -ForegroundColor Cyan
    Write-Host "-----------" -ForegroundColor Cyan
    
    $allLogs = Get-Content $AppLog
    $analyzeCount = ($allLogs | Where-Object { $_ -match "Analyze request" }).Count
    $downloadCount = ($allLogs | Where-Object { $_ -match "Download task.*started" }).Count
    $completedCount = ($allLogs | Where-Object { $_ -match "finished with status=finished" }).Count
    $errorCount = ($allLogs | Where-Object { $_ -match "ERROR" }).Count
    
    Write-Host "📊 Total Analysis Requests: $analyzeCount" -ForegroundColor White
    Write-Host "📊 Total Downloads Started: $downloadCount" -ForegroundColor White
    Write-Host "📊 Total Downloads Completed: $completedCount" -ForegroundColor White
    Write-Host "📊 Total Errors: $errorCount" -ForegroundColor White
    
    # Platform breakdown
    $youtubeCount = ($allLogs | Where-Object { $_ -match "platform=youtube" }).Count
    $instagramCount = ($allLogs | Where-Object { $_ -match "platform=instagram" }).Count
    $tiktokCount = ($allLogs | Where-Object { $_ -match "platform=tiktok" }).Count
    $facebookCount = ($allLogs | Where-Object { $_ -match "platform=facebook" }).Count
    
    Write-Host ""
    Write-Host "PLATFORM USAGE:" -ForegroundColor Cyan
    Write-Host "---------------" -ForegroundColor Cyan
    Write-Host "📺 YouTube: $youtubeCount requests" -ForegroundColor White
    Write-Host "📸 Instagram: $instagramCount requests" -ForegroundColor White
    Write-Host "🎵 TikTok: $tiktokCount requests" -ForegroundColor White
    Write-Host "📘 Facebook: $facebookCount requests" -ForegroundColor White
    
} else {
    Write-Host "❌ No log file found at: $AppLog" -ForegroundColor Red
}

Write-Host ""
Write-Host "💡 To monitor live activity, run: .\monitor_logs.ps1" -ForegroundColor Yellow