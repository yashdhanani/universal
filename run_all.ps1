Param(
  [int]$ApiPort = 8000,
  [switch]$Install,
  [switch]$NoCelery
)

$ErrorActionPreference = 'Stop'

$Root = "e:\project\downloader"
$Venv = Join-Path $Root "venv"
$Py = Join-Path $Venv "Scripts\python.exe"
$Pip = Join-Path $Venv "Scripts\pip.exe"
$Uvicorn = Join-Path $Venv "Scripts\uvicorn.exe"
$Celery = Join-Path $Venv "Scripts\celery.exe"

# Optional install step
if ($Install) {
  Write-Host "[1/5] Installing dependencies..." -ForegroundColor Cyan
  & $Py -m pip install --upgrade pip
  & $Pip install -r (Join-Path $Root "requirements.txt")
}

# Check Redis URL and reachability (optional)
$RedisUrl = $env:REDIS_URL
if (-not $RedisUrl) { $RedisUrl = "redis://localhost:6379/0" }
Write-Host "[i] Using REDIS_URL=$RedisUrl" -ForegroundColor DarkGray

function Test-TcpPort {
  param(
    [Parameter(Mandatory=$true)][string]$Host,
    [Parameter(Mandatory=$true)][int]$Port,
    [int]$TimeoutMs = 700
  )
  try {
    $client = New-Object System.Net.Sockets.TcpClient
    $ar = $client.BeginConnect($Host, $Port, $null, $null)
    $ok = $ar.AsyncWaitHandle.WaitOne($TimeoutMs, $false)
    if ($ok -and $client.Connected) { $client.EndConnect($ar); $client.Close(); return $true }
    $client.Close(); return $false
  } catch { return $false }
}

$RedisReachable = $false
if (-not $NoCelery) {
  try {
    $uri = [uri]$RedisUrl
    $host = $uri.Host
    $port = if ($uri.Port -gt 0) { $uri.Port } else { 6379 }
    $RedisReachable = Test-TcpPort -Host $host -Port $port -TimeoutMs 700
  } catch { $RedisReachable = $false }
}

# Start API (Uvicorn)
Write-Host "[2/5] Starting API on http://127.0.0.1:$ApiPort ..." -ForegroundColor Cyan
$apiJob = Start-Job -Name "api" -ScriptBlock {
  param($Uvicorn, $Root, $ApiPort)
  Set-Location $Root
  & $Uvicorn "main_api:APP" --host 127.0.0.1 --port $ApiPort --reload 2>&1
} -ArgumentList $Uvicorn, $Root, $ApiPort

Start-Sleep -Milliseconds 800

# Start Celery worker only if Redis is reachable and not disabled
if ($NoCelery) {
  Write-Host "[3/5] Skipping Celery (NoCelery flag set). Using in-process background tasks." -ForegroundColor Yellow
} elseif ($RedisReachable) {
  Write-Host "[3/5] Starting Celery worker ..." -ForegroundColor Cyan
  $celeryJob = Start-Job -Name "celery" -ScriptBlock {
    param($Celery, $Root)
    Set-Location $Root
    & $Celery -A backend.tasks.celery_app.celery worker -P solo --loglevel=info 2>&1
  } -ArgumentList $Celery, $Root
} else {
  Write-Host "[3/5] Redis not reachable. Skipping Celery; app will fall back to in-process background tasks." -ForegroundColor Yellow
}

# Open browser
Write-Host "[4/5] Opening UI ..." -ForegroundColor Cyan
Start-Process "http://127.0.0.1:$ApiPort/universal_tailwind"

Write-Host "[5/5] Streaming logs. Press Ctrl+C to stop and cleanup." -ForegroundColor Yellow
try {
  while ($true) {
    Receive-Job -Name api -Keep
    if (Get-Job -Name celery -ErrorAction SilentlyContinue) {
      Receive-Job -Name celery -Keep
    }
    Start-Sleep -Seconds 1
  }
} finally {
  Write-Host "\nStopping jobs..." -ForegroundColor Yellow
  Get-Job -Name api,celery -ErrorAction SilentlyContinue | Stop-Job -PassThru | Remove-Job -Force -ErrorAction SilentlyContinue | Out-Null
}