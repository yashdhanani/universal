# Website Activity Log Monitor
# This script monitors your YouTube downloader application logs in real-time

param(
    [string]$LogType = "all"  # Options: all, app, uvicorn, errors
)

$LogsDir = "e:\project\downloader\logs"
$AppLog = Join-Path $LogsDir "app.log"
$UvicornLog = Join-Path $LogsDir "uvicorn.err"

Write-Host "=== YouTube Downloader - Website Activity Monitor ===" -ForegroundColor Green
Write-Host "Monitoring logs in: $LogsDir" -ForegroundColor Yellow
Write-Host "Press Ctrl+C to stop monitoring" -ForegroundColor Yellow
Write-Host ""

function Show-RecentActivity {
    Write-Host "=== RECENT ACTIVITY (Last 20 entries) ===" -ForegroundColor Cyan
    
    if (Test-Path $AppLog) {
        Write-Host "--- Application Activity ---" -ForegroundColor Green
        Get-Content $AppLog -Tail 20 | ForEach-Object {
            $line = $_
            if ($line -match "INFO.*Analyze request") {
                Write-Host $line -ForegroundColor Green
            } elseif ($line -match "ERROR") {
                Write-Host $line -ForegroundColor Red
            } elseif ($line -match "WARNING") {
                Write-Host $line -ForegroundColor Yellow
            } elseif ($line -match "Download task.*started") {
                Write-Host $line -ForegroundColor Magenta
            } elseif ($line -match "finished with status") {
                Write-Host $line -ForegroundColor Blue
            } else {
                Write-Host $line -ForegroundColor White
            }
        }
    }
    
    Write-Host ""
    Write-Host "--- Server Status ---" -ForegroundColor Green
    if (Test-Path $UvicornLog) {
        Get-Content $UvicornLog -Tail 5 | ForEach-Object {
            Write-Host $_ -ForegroundColor Cyan
        }
    }
    Write-Host ""
}

function Monitor-LiveLogs {
    Write-Host "=== LIVE MONITORING (New entries will appear below) ===" -ForegroundColor Cyan
    Write-Host ""
    
    # Monitor app.log for new entries
    if (Test-Path $AppLog) {
        Get-Content $AppLog -Wait -Tail 0 | ForEach-Object {
            $timestamp = Get-Date -Format "HH:mm:ss"
            $line = $_
            
            if ($line -match "INFO.*Analyze request.*platform=(\w+).*url=([^,]+)") {
                $platform = $matches[1]
                $url = $matches[2]
                Write-Host "[$timestamp] 🔍 NEW REQUEST: $platform - $url" -ForegroundColor Green
            } elseif ($line -match "Download task ([\w-]+) started") {
                $taskId = $matches[1]
                Write-Host "[$timestamp] ⬇️  DOWNLOAD STARTED: Task $taskId" -ForegroundColor Magenta
            } elseif ($line -match "Task ([\w-]+) finished with status=(\w+)") {
                $taskId = $matches[1]
                $status = $matches[2]
                Write-Host "[$timestamp] ✅ DOWNLOAD COMPLETED: Task $taskId ($status)" -ForegroundColor Blue
            } elseif ($line -match "ERROR") {
                Write-Host "[$timestamp] ❌ ERROR: $line" -ForegroundColor Red
            } elseif ($line -match "WARNING") {
                Write-Host "[$timestamp] ⚠️  WARNING: $line" -ForegroundColor Yellow
            } elseif ($line -match "Client '(\w+)' yielded total=(\d+) usable=(\d+)") {
                $client = $matches[1]
                $total = $matches[2]
                $usable = $matches[3]
                Write-Host "[$timestamp] 📊 FORMAT INFO: $client client found $usable/$total formats" -ForegroundColor White
            } else {
                Write-Host "[$timestamp] $line" -ForegroundColor Gray
            }
        }
    }
}

# Show current server status
Write-Host "=== SERVER STATUS ===" -ForegroundColor Cyan
$serverRunning = Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*uvicorn*" }
if ($serverRunning) {
    Write-Host "✅ Server is RUNNING on http://127.0.0.1:5000" -ForegroundColor Green
    Write-Host "✅ Frontend available at: http://127.0.0.1:5000/universal_tailwind" -ForegroundColor Green
} else {
    Write-Host "❌ Server appears to be STOPPED" -ForegroundColor Red
}
Write-Host ""

# Show recent activity first
Show-RecentActivity

# Start live monitoring
Monitor-LiveLogs