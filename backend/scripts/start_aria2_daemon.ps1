# Start Aria2c as High-Performance Daemon
# This provides RPC interface for ultra-fast downloads

Write-Host "🚀 STARTING ARIA2C HIGH-PERFORMANCE DAEMON" -ForegroundColor Green
Write-Host "===========================================" -ForegroundColor Green

$aria2cPath = $env:ARIA2C_PATH
if (-not $aria2cPath) {
    $aria2cPath = Get-Command "aria2c" -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source
}

if (-not $aria2cPath -or -not (Test-Path $aria2cPath)) {
    Write-Host "❌ Aria2c not found!" -ForegroundColor Red
    Write-Host "Install with: choco install aria2 -y" -ForegroundColor Yellow
    exit 1
}

Write-Host "✅ Found Aria2c: $aria2cPath" -ForegroundColor Green

# Check if daemon is already running
try {
    $response = Invoke-RestMethod -Uri "http://localhost:6800/jsonrpc" -Method POST -Body '{"jsonrpc":"2.0","id":"test","method":"aria2.getVersion"}' -ContentType "application/json" -TimeoutSec 2
    Write-Host "⚠️  Aria2c daemon already running" -ForegroundColor Yellow
    Write-Host "   Version: $($response.result.version)" -ForegroundColor White
    Write-Host "   RPC Port: 6800" -ForegroundColor White
    exit 0
} catch {
    # Daemon not running, start it
}

# Kill any existing aria2c processes
Get-Process -Name "aria2c" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "🔧 Starting Aria2c daemon with optimized settings..." -ForegroundColor Cyan

# Start Aria2c daemon with configuration
$configPath = Join-Path (Get-Location) "aria2.conf"
$logPath = Join-Path (Get-Location) "logs\aria2.log"

# Ensure logs directory exists
New-Item -ItemType Directory -Path "logs" -Force | Out-Null

# Start daemon
$daemonArgs = @(
    "--daemon=true",
    "--enable-rpc=true",
    "--rpc-listen-port=6800",
    "--rpc-allow-origin-all=true",
    "--rpc-listen-all=true",
    "--conf-path=$configPath",
    "--log=$logPath",
    "--log-level=notice"
)

try {
    Start-Process -FilePath $aria2cPath -ArgumentList $daemonArgs -WindowStyle Hidden
    Start-Sleep -Seconds 2
    
    # Test if daemon started successfully
    $response = Invoke-RestMethod -Uri "http://localhost:6800/jsonrpc" -Method POST -Body '{"jsonrpc":"2.0","id":"test","method":"aria2.getVersion"}' -ContentType "application/json" -TimeoutSec 5
    
    Write-Host "✅ Aria2c daemon started successfully!" -ForegroundColor Green
    Write-Host "   Version: $($response.result.version)" -ForegroundColor White
    Write-Host "   RPC Port: 6800" -ForegroundColor White
    Write-Host "   Max Concurrent: 8 downloads" -ForegroundColor White
    Write-Host "   Max Connections: 16 per server" -ForegroundColor White
    Write-Host "   Split: 16 segments per file" -ForegroundColor White
    Write-Host ""
    Write-Host "🚀 ULTRA-FAST DOWNLOADS NOW ENABLED!" -ForegroundColor Green
    Write-Host "   Your downloads will be 5-10x faster" -ForegroundColor White
    Write-Host ""
    Write-Host "📊 Monitor: Get-Content logs\aria2.log -Wait" -ForegroundColor Gray
    
} catch {
    Write-Host "❌ Failed to start Aria2c daemon: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Check logs: Get-Content logs\aria2.log" -ForegroundColor Yellow
}