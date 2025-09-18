# One-command runner for Enhanced 41-URL Test

# ----------------------------
# Configurable environment vars
# ----------------------------
# Path to Netscape-format cookies file (optional for restricted platforms)
# $env:COOKIES_FILE = "e:\\project\\downloader\\cookies.txt"

# Override defaults if needed
# $env:INFO_BASE = "http://127.0.0.1:8004/api/info"
# $env:INFO_OUTFILE = "tools/reports/run_41_urls_enhanced.json"
# $env:INFO_TIMEOUT = "60"
# $env:INFO_PUBLIC_TIMEOUT = "45"
# $env:INFO_RESTRICTED_TIMEOUT = "90"
# $env:INFO_RETRIES = "2"
# $env:INFO_RETRY_BACKOFF = "1.5"
# $env:INFO_CONCURRENCY = "6"

# Move to project root
Set-Location "e:\project\downloader"

# Activate virtual environment
& .\venv\Scripts\Activate.ps1

# Choose a free port (prefer $env:INFO_PORT or 8004)
$desiredPort = if ($env:INFO_PORT) { [int]$env:INFO_PORT } else { 8004 }

function Get-FreePort([int]$startPort) {
    $port = $startPort
    while ($true) {
        $inUse = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
        if (-not $inUse) { return $port }
        $port += 1
        if ($port -gt 65535) { throw "No free port found" }
    }
}

$port = Get-FreePort $desiredPort

# If desired port was busy, try stopping owners once and re-check
if ($port -ne $desiredPort) {
    try {
        $conns = Get-NetTCPConnection -LocalPort $desiredPort -ErrorAction SilentlyContinue
        if ($conns) {
            $pids = $conns | Select-Object -ExpandProperty OwningProcess -Unique
            foreach ($pid in $pids) {
                try {
                    $proc = Get-Process -Id $pid -ErrorAction SilentlyContinue
                    if ($proc) {
                        Write-Host "Stopping process PID=$pid using port $desiredPort ..."
                        Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
                        Start-Sleep -Milliseconds 300
                    }
                } catch {}
            }
            $freeNow = -not (Get-NetTCPConnection -LocalPort $desiredPort -ErrorAction SilentlyContinue)
            if ($freeNow) { $port = $desiredPort }
        }
    } catch {}
}

# Start API in background
Write-Host "Starting API on http://127.0.0.1:$port ..."
Start-Process -NoNewWindow -FilePath "python" -ArgumentList "-m uvicorn main_api:APP --host 127.0.0.1 --port $port"
Start-Sleep -Seconds 3

# Determine concurrency from env or fallback
$concurrency = if ($env:INFO_CONCURRENCY) { [int]$env:INFO_CONCURRENCY } else { 6 }

# Run enhanced 41-URL test on the selected port
python tools/run_41_urls_enhanced.py --concurrency $concurrency --base "http://127.0.0.1:$port/api/info"