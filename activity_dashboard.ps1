# YouTube Downloader Activity Dashboard
# Shows statistics and current status of your application

$LogsDir = "e:\project\downloader\logs"
$DownloadsDir = "e:\project\downloader\downloads"
$AppLog = Join-Path $LogsDir "app.log"

function Show-Dashboard {
    Clear-Host
    Write-Host "╔══════════════════════════════════════════════════════════════╗" -ForegroundColor Green
    Write-Host "║              YouTube Downloader - Activity Dashboard         ║" -ForegroundColor Green  
    Write-Host "╚══════════════════════════════════════════════════════════════╝" -ForegroundColor Green
    Write-Host ""
    
    # Server Status
    Write-Host "🖥️  SERVER STATUS" -ForegroundColor Cyan
    Write-Host "─────────────────" -ForegroundColor Cyan
    $serverProcess = Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object { $_.ProcessName -eq "python" }
    if ($serverProcess) {
        Write-Host "✅ Status: RUNNING" -ForegroundColor Green
        Write-Host "🌐 URL: http://127.0.0.1:5000" -ForegroundColor White
        Write-Host "🎨 Frontend: http://127.0.0.1:5000/universal_tailwind" -ForegroundColor White
        Write-Host "⏰ Process ID: $($serverProcess.Id)" -ForegroundColor White
    } else {
        Write-Host "❌ Status: STOPPED" -ForegroundColor Red
    }
    Write-Host ""
    
    # Recent Activity Statistics
    if (Test-Path $AppLog) {
        Write-Host "📊 ACTIVITY STATISTICS (Recent)" -ForegroundColor Cyan
        Write-Host "──────────────────────────────────" -ForegroundColor Cyan
        
        $logContent = Get-Content $AppLog -Tail 100
        
        $analyzeRequests = ($logContent | Where-Object { $_ -match "Analyze request" }).Count
        $downloadTasks = ($logContent | Where-Object { $_ -match "Download task.*started" }).Count
        $completedTasks = ($logContent | Where-Object { $_ -match "finished with status=finished" }).Count
        $errors = ($logContent | Where-Object { $_ -match "ERROR" }).Count
        $warnings = ($logContent | Where-Object { $_ -match "WARNING" }).Count
        
        Write-Host "🔍 Analysis Requests: $analyzeRequests" -ForegroundColor White
        Write-Host "⬇️  Download Tasks Started: $downloadTasks" -ForegroundColor White
        Write-Host "✅ Downloads Completed: $completedTasks" -ForegroundColor Green
        Write-Host "❌ Errors: $errors" -ForegroundColor $(if($errors -gt 0) { "Red" } else { "White" })
        Write-Host "⚠️  Warnings: $warnings" -ForegroundColor $(if($warnings -gt 0) { "Yellow" } else { "White" })
        
        # Platform breakdown
        $youtubeRequests = ($logContent | Where-Object { $_ -match "platform=youtube" }).Count
        $instagramRequests = ($logContent | Where-Object { $_ -match "platform=instagram" }).Count
        $tiktokRequests = ($logContent | Where-Object { $_ -match "platform=tiktok" }).Count
        $facebookRequests = ($logContent | Where-Object { $_ -match "platform=facebook" }).Count
        $twitterRequests = ($logContent | Where-Object { $_ -match "platform=twitter" }).Count
        
        Write-Host ""
        Write-Host "🎯 PLATFORM BREAKDOWN" -ForegroundColor Cyan
        Write-Host "─────────────────────" -ForegroundColor Cyan
        Write-Host "📺 YouTube: $youtubeRequests requests" -ForegroundColor White
        Write-Host "📸 Instagram: $instagramRequests requests" -ForegroundColor White
        Write-Host "🎵 TikTok: $tiktokRequests requests" -ForegroundColor White
        Write-Host "📘 Facebook: $facebookRequests requests" -ForegroundColor White
        Write-Host "🐦 Twitter: $twitterRequests requests" -ForegroundColor White
    }
    
    Write-Host ""
    
    # Download Directory Stats
    if (Test-Path $DownloadsDir) {
        Write-Host "📁 DOWNLOAD DIRECTORY" -ForegroundColor Cyan
        Write-Host "────────────────────" -ForegroundColor Cyan
        
        $allFiles = Get-ChildItem -Path $DownloadsDir -Recurse -File -ErrorAction SilentlyContinue
        $totalFiles = $allFiles.Count
        if ($allFiles) {
            $totalSize = ($allFiles | Measure-Object -Property Length -Sum).Sum
            $totalSizeMB = [math]::Round($totalSize / 1MB, 2)
        } else {
            $totalSizeMB = 0
        }
        
        Write-Host "📄 Total Files: $totalFiles" -ForegroundColor White
        Write-Host "💾 Total Size: $totalSizeMB MB" -ForegroundColor White
        
        # Recent downloads (last 24 hours)
        if ($allFiles) {
            $recentFiles = $allFiles | Where-Object { $_.LastWriteTime -gt (Get-Date).AddDays(-1) }
            Write-Host "🆕 Recent Downloads (24h): $($recentFiles.Count)" -ForegroundColor White
        }
    }
    
    Write-Host ""
    
    # Recent Activity
    if (Test-Path $AppLog) {
        Write-Host "🕒 RECENT ACTIVITY (Last 10 entries)" -ForegroundColor Cyan
        Write-Host "────────────────────────────────────" -ForegroundColor Cyan
        
        Get-Content $AppLog -Tail 10 | ForEach-Object {
            $line = $_
            if ($line -match "Analyze request.*platform=(\w+)") {
                $platform = $matches[1]
                Write-Host "🔍 Analysis: $platform" -ForegroundColor Green
            } elseif ($line -match "Download task.*started") {
                Write-Host "⬇️  Download started" -ForegroundColor Magenta
            } elseif ($line -match "finished with status=finished") {
                Write-Host "✅ Download completed" -ForegroundColor Blue
            } elseif ($line -match "ERROR") {
                Write-Host "❌ Error occurred" -ForegroundColor Red
            } else {
                Write-Host $line.Substring(0, [Math]::Min(80, $line.Length)) -ForegroundColor Gray
            }
        }
    }
    
    Write-Host ""
    Write-Host "🔄 Press Ctrl+C to exit. Refreshing in 5 seconds..." -ForegroundColor Yellow
}

# Show dashboard once
Show-Dashboard