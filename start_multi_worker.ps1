# Start FastAPI with Multiple Workers for Maximum Concurrency
# This dramatically improves performance under load

param(
    [int]$Workers = 4,
    [int]$Port = 8000,
    [switch]$WithAria2c
)

Write-Host "🚀 STARTING MULTI-WORKER HIGH-PERFORMANCE SERVER" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green
Write-Host ""

$Root = "e:\project\downloader"
Set-Location $Root

# Start Aria2c daemon if requested
if ($WithAria2c) {
    Write-Host "⚡ Starting Aria2c daemon..." -ForegroundColor Cyan
    .\start_aria2_daemon.ps1
    Write-Host ""
}

# Load environment
if (Test-Path ".env") {
    Get-Content ".env" | ForEach-Object {
        if ($_ -match "^([^#][^=]+)=(.*)$") {
            [Environment]::SetEnvironmentVariable($matches[1], $matches[2], "Process")
        }
    }
}

# Set performance environment variables
$env:FAST_DEV = "1"
$env:PYTHONUNBUFFERED = "1"
$env:UVICORN_WORKERS = $Workers.ToString()

$Venv = Join-Path $Root "venv"
$Uvicorn = Join-Path $Venv "Scripts\uvicorn.exe"

Write-Host "🔧 Configuration:" -ForegroundColor Cyan
Write-Host "   Workers: $Workers" -ForegroundColor White
Write-Host "   Port: $Port" -ForegroundColor White
Write-Host "   Aria2c: $(if($WithAria2c){'Enabled'}else{'Disabled'})" -ForegroundColor White
Write-Host ""

# Kill existing processes
Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object { $_.ProcessName -eq "python" } | Stop-Process -Force -ErrorAction SilentlyContinue

Write-Host "🚀 Starting multi-worker server..." -ForegroundColor Green

# Start server with multiple workers
$serverArgs = @(
    "main_api:APP",
    "--host", "127.0.0.1",
    "--port", $Port.ToString(),
    "--workers", $Workers.ToString(),
    "--worker-class", "uvicorn.workers.UvicornWorker",
    "--access-log",
    "--log-level", "info"
)

try {
    & $Uvicorn @serverArgs
} catch {
    Write-Host "❌ Failed to start server: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
    Write-Host "🔧 Troubleshooting:" -ForegroundColor Yellow
    Write-Host "1. Check if port $Port is available" -ForegroundColor White
    Write-Host "2. Verify uvicorn installation: pip install uvicorn[standard]" -ForegroundColor White
    Write-Host "3. Try single worker: .\run_all.ps1" -ForegroundColor White
}