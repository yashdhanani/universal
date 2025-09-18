# Quick Speed Optimization
Write-Host "⚡ QUICK SPEED OPTIMIZATION" -ForegroundColor Green
Write-Host "==========================" -ForegroundColor Green

# Update .env with optimized settings
$envContent = @"
# OPTIMIZED CONFIGURATION FOR MAXIMUM SPEED
COOKIES_FILE=e:\project\downloader\cookies.txt
FFMPEG_LOCATION=C:\ProgramData\chocolatey\bin
ARIA2C_PATH=
ARIA2C_THREADS=16
ARIA2C_MAX_CONNECTIONS=16
USER_AGENT=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36
ACCEPT_LANGUAGE=en-US,en;q=0.9
SECRET_KEY=dev-super-secret-key-change-in-production-12345
REDIS_URL=redis://localhost:6379/0
FAST_DEV=1
SKIP_UPDATE=1
SKIP_TESTS=1
CONCURRENT_DOWNLOADS=4
HTTP_CHUNK_SIZE=10485760
SOCKET_TIMEOUT=10
RETRIES=2
MAX_CONCURRENT_FRAGMENTS=8
FRAGMENT_RETRIES=3
"@

$envContent | Out-File -FilePath ".env" -Encoding UTF8 -Force
Write-Host "✅ Configuration optimized" -ForegroundColor Green

# Try to find and set Aria2c path
$aria2cLocations = @(
    "C:\ProgramData\chocolatey\bin\aria2c.exe",
    "C:\Tools\aria2\aria2c.exe",
    "aria2c.exe"
)

foreach ($location in $aria2cLocations) {
    try {
        if ($location -eq "aria2c.exe") {
            $testResult = Get-Command "aria2c" -ErrorAction SilentlyContinue
            if ($testResult) {
                $aria2cPath = $testResult.Source
                Write-Host "✅ Found Aria2c at: $aria2cPath" -ForegroundColor Green
                (Get-Content ".env") -replace "ARIA2C_PATH=", "ARIA2C_PATH=$aria2cPath" | Set-Content ".env"
                break
            }
        } elseif (Test-Path $location) {
            Write-Host "✅ Found Aria2c at: $location" -ForegroundColor Green
            (Get-Content ".env") -replace "ARIA2C_PATH=", "ARIA2C_PATH=$location" | Set-Content ".env"
            break
        }
    } catch {
        continue
    }
}

Write-Host ""
Write-Host "🎉 OPTIMIZATION COMPLETE!" -ForegroundColor Green
Write-Host "Now run: .\start_fast.ps1" -ForegroundColor Yellow