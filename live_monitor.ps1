# Live Activity Monitor for YouTube Downloader
# Monitors logs in real-time

$AppLog = "e:\project\downloader\logs\app.log"

Write-Host "=== LIVE ACTIVITY MONITOR ===" -ForegroundColor Green
Write-Host "Monitoring: $AppLog" -ForegroundColor Yellow
Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow
Write-Host ""

# Show current status
Write-Host "Current Status:" -ForegroundColor Cyan
$pythonProcesses = Get-Process -Name "python" -ErrorAction SilentlyContinue
if ($pythonProcesses) {
    Write-Host "✅ Server RUNNING at http://127.0.0.1:5000/universal_tailwind" -ForegroundColor Green
} else {
    Write-Host "❌ Server STOPPED" -ForegroundColor Red
}
Write-Host ""
Write-Host "Live Activity Feed:" -ForegroundColor Cyan
Write-Host "-------------------" -ForegroundColor Cyan

# Monitor log file for new entries
if (Test-Path $AppLog) {
    Get-Content $AppLog -Wait -Tail 0 | ForEach-Object {
        $timestamp = Get-Date -Format "HH:mm:ss"
        $line = $_
        
        if ($line -like "*Analyze request*youtube*") {
            Write-Host "[$timestamp] 🔍 YouTube Analysis Request" -ForegroundColor Green
        } elseif ($line -like "*Analyze request*instagram*") {
            Write-Host "[$timestamp] 🔍 Instagram Analysis Request" -ForegroundColor Green  
        } elseif ($line -like "*Analyze request*tiktok*") {
            Write-Host "[$timestamp] 🔍 TikTok Analysis Request" -ForegroundColor Green
        } elseif ($line -like "*Download task*started*") {
            Write-Host "[$timestamp] ⬇️  Download Started" -ForegroundColor Magenta
        } elseif ($line -like "*finished with status=finished*") {
            Write-Host "[$timestamp] ✅ Download Completed Successfully" -ForegroundColor Blue
        } elseif ($line -like "*ERROR*") {
            Write-Host "[$timestamp] ❌ ERROR: $line" -ForegroundColor Red
        } elseif ($line -like "*WARNING*") {
            Write-Host "[$timestamp] ⚠️  WARNING: $line" -ForegroundColor Yellow
        } elseif ($line -like "*Client*yielded*") {
            Write-Host "[$timestamp] 📊 Format extraction completed" -ForegroundColor White
        } else {
            Write-Host "[$timestamp] $line" -ForegroundColor Gray
        }
    }
} else {
    Write-Host "❌ Log file not found: $AppLog" -ForegroundColor Red
}