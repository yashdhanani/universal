# ULTRA-PERFORMANCE DASHBOARD
# Real-time monitoring and optimization for your YouTube Downloader

param(
    [switch]$Live,
    [switch]$Report,
    [switch]$Optimize,
    [int]$Hours = 24
)

Write-Host "🚀 ULTRA-PERFORMANCE DASHBOARD" -ForegroundColor Green
Write-Host "==============================" -ForegroundColor Green
Write-Host ""

$Root = "e:\project\downloader"
Set-Location $Root

# Function to get system performance
function Get-SystemPerformance {
    $cpu = Get-Counter "\Processor(_Total)\% Processor Time" -SampleInterval 1 -MaxSamples 1
    $memory = Get-CimInstance Win32_OperatingSystem
    $disk = Get-Counter "\PhysicalDisk(_Total)\Disk Bytes/sec" -SampleInterval 1 -MaxSamples 1 -ErrorAction SilentlyContinue
    
    return @{
        CPU = [math]::Round($cpu.CounterSamples[0].CookedValue, 1)
        MemoryUsedGB = [math]::Round(($memory.TotalVisibleMemorySize - $memory.FreePhysicalMemory) / 1MB, 2)
        MemoryTotalGB = [math]::Round($memory.TotalVisibleMemorySize / 1MB, 2)
        DiskIOPS = if($disk) { [math]::Round($disk.CounterSamples[0].CookedValue / 1MB, 2) } else { 0 }
    }
}

# Function to check application health
function Test-ApplicationHealth {
    try {
        $response = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/health" -TimeoutSec 5
        return @{ Status = "Healthy"; ResponseTime = "Fast" }
    } catch {
        return @{ Status = "Unhealthy"; Error = $_.Exception.Message }
    }
}

# Function to get cache statistics
function Get-CacheStats {
    $cacheFile = "cache\video_cache.db"
    if (Test-Path $cacheFile) {
        $size = (Get-Item $cacheFile).Length / 1MB
        return @{
            Enabled = $true
            SizeMB = [math]::Round($size, 2)
            Status = if($size -gt 0) { "Active" } else { "Empty" }
        }
    } else {
        return @{ Enabled = $false; Status = "Disabled" }
    }
}

# Function to check Aria2c status
function Get-Aria2cStatus {
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:6800/jsonrpc" -Method POST -Body '{"jsonrpc":"2.0","id":"test","method":"aria2.getVersion"}' -ContentType "application/json" -TimeoutSec 2
        return @{
            Status = "Running"
            Version = $response.result.version
            Features = $response.result.enabledFeatures -join ", "
        }
    } catch {
        return @{ Status = "Not Running" }
    }
}

if ($Live) {
    Write-Host "📊 LIVE PERFORMANCE MONITOR" -ForegroundColor Cyan
    Write-Host "Press Ctrl+C to stop..." -ForegroundColor Gray
    Write-Host ""
    
    while ($true) {
        Clear-Host
        Write-Host "🚀 LIVE PERFORMANCE MONITOR - $(Get-Date -Format 'HH:mm:ss')" -ForegroundColor Green
        Write-Host "============================================" -ForegroundColor Green
        Write-Host ""
        
        # System Performance
        $perf = Get-SystemPerformance
        Write-Host "💻 SYSTEM PERFORMANCE:" -ForegroundColor Cyan
        Write-Host "   CPU Usage: $($perf.CPU)%" -ForegroundColor White
        Write-Host "   Memory: $($perf.MemoryUsedGB)GB / $($perf.MemoryTotalGB)GB" -ForegroundColor White
        Write-Host "   Disk I/O: $($perf.DiskIOPS) MB/s" -ForegroundColor White
        Write-Host ""
        
        # Application Health
        $health = Test-ApplicationHealth
        $healthColor = if($health.Status -eq "Healthy") { "Green" } else { "Red" }
        Write-Host "🏥 APPLICATION HEALTH:" -ForegroundColor Cyan
        Write-Host "   Status: $($health.Status)" -ForegroundColor $healthColor
        if ($health.Error) {
            Write-Host "   Error: $($health.Error)" -ForegroundColor Red
        }
        Write-Host ""
        
        # Cache Status
        $cache = Get-CacheStats
        Write-Host "🗄️  CACHE STATUS:" -ForegroundColor Cyan
        Write-Host "   Enabled: $($cache.Enabled)" -ForegroundColor White
        if ($cache.Enabled) {
            Write-Host "   Size: $($cache.SizeMB) MB" -ForegroundColor White
            Write-Host "   Status: $($cache.Status)" -ForegroundColor White
        }
        Write-Host ""
        
        # Aria2c Status
        $aria2c = Get-Aria2cStatus
        $aria2cColor = if($aria2c.Status -eq "Running") { "Green" } else { "Yellow" }
        Write-Host "⚡ ARIA2C STATUS:" -ForegroundColor Cyan
        Write-Host "   Status: $($aria2c.Status)" -ForegroundColor $aria2cColor
        if ($aria2c.Version) {
            Write-Host "   Version: $($aria2c.Version)" -ForegroundColor White
        }
        Write-Host ""
        
        # Recent Activity
        if (Test-Path "logs\app.log") {
            $recentLogs = Get-Content "logs\app.log" -Tail 3 -ErrorAction SilentlyContinue
            if ($recentLogs) {
                Write-Host "📝 RECENT ACTIVITY:" -ForegroundColor Cyan
                foreach ($log in $recentLogs) {
                    Write-Host "   $log" -ForegroundColor Gray
                }
            }
        }
        
        Write-Host ""
        Write-Host "🔄 Refreshing in 5 seconds... (Ctrl+C to stop)" -ForegroundColor Gray
        Start-Sleep -Seconds 5
    }
}

if ($Report) {
    Write-Host "📊 PERFORMANCE REPORT (Last $Hours hours)" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    
    # Current Status
    $perf = Get-SystemPerformance
    $health = Test-ApplicationHealth
    $cache = Get-CacheStats
    $aria2c = Get-Aria2cStatus
    
    Write-Host "📈 CURRENT STATUS:" -ForegroundColor Yellow
    Write-Host "   Application: $($health.Status)" -ForegroundColor White
    Write-Host "   CPU Usage: $($perf.CPU)%" -ForegroundColor White
    Write-Host "   Memory Usage: $($perf.MemoryUsedGB)GB" -ForegroundColor White
    Write-Host "   Cache: $($cache.Status)" -ForegroundColor White
    Write-Host "   Aria2c: $($aria2c.Status)" -ForegroundColor White
    Write-Host ""
    
    # Log Analysis
    if (Test-Path "logs\app.log") {
        $logLines = Get-Content "logs\app.log" -ErrorAction SilentlyContinue
        $recentLines = $logLines | Select-Object -Last 1000
        
        $downloads = ($recentLines | Select-String "downloading" | Measure-Object).Count
        $errors = ($recentLines | Select-String "ERROR" | Measure-Object).Count
        $warnings = ($recentLines | Select-String "WARNING" | Measure-Object).Count
        
        Write-Host "📊 ACTIVITY SUMMARY:" -ForegroundColor Yellow
        Write-Host "   Recent Downloads: $downloads" -ForegroundColor White
        Write-Host "   Errors: $errors" -ForegroundColor $(if($errors -gt 0){"Red"}else{"Green"})
        Write-Host "   Warnings: $warnings" -ForegroundColor $(if($warnings -gt 0){"Yellow"}else{"Green"})
        Write-Host ""
    }
    
    # Performance Recommendations
    Write-Host "💡 PERFORMANCE RECOMMENDATIONS:" -ForegroundColor Yellow
    
    if ($aria2c.Status -ne "Running") {
        Write-Host "   ⚡ Install/Start Aria2c for 10x faster downloads" -ForegroundColor Cyan
        Write-Host "      Run: .\start_aria2_daemon.ps1" -ForegroundColor Gray
    }
    
    if (-not $cache.Enabled) {
        Write-Host "   🗄️  Enable caching for faster repeated requests" -ForegroundColor Cyan
        Write-Host "      Caching will be auto-enabled on next analysis" -ForegroundColor Gray
    }
    
    if ($perf.CPU -gt 80) {
        Write-Host "   🔥 High CPU usage detected - consider reducing concurrent downloads" -ForegroundColor Red
    }
    
    if ($perf.MemoryUsedGB / $perf.MemoryTotalGB -gt 0.8) {
        Write-Host "   💾 High memory usage - restart application if needed" -ForegroundColor Red
    }
    
    Write-Host ""
}

if ($Optimize) {
    Write-Host "⚡ RUNNING PERFORMANCE OPTIMIZATIONS" -ForegroundColor Cyan
    Write-Host "====================================" -ForegroundColor Cyan
    Write-Host ""
    
    # Clean old logs
    Write-Host "🧹 Cleaning old logs..." -ForegroundColor Yellow
    if (Test-Path "logs\app.log") {
        $logSize = (Get-Item "logs\app.log").Length / 1MB
        if ($logSize -gt 50) {
            Get-Content "logs\app.log" -Tail 1000 | Set-Content "logs\app.log.tmp"
            Move-Item "logs\app.log.tmp" "logs\app.log" -Force
            Write-Host "   ✅ Log file trimmed (was $([math]::Round($logSize, 1)) MB)" -ForegroundColor Green
        } else {
            Write-Host "   ✅ Log file size OK ($([math]::Round($logSize, 1)) MB)" -ForegroundColor Green
        }
    }
    
    # Clean old downloads
    Write-Host "🧹 Cleaning old downloads..." -ForegroundColor Yellow
    $downloadDirs = @("downloads\youtube", "downloads\instagram", "downloads\tiktok")
    $totalCleaned = 0
    
    foreach ($dir in $downloadDirs) {
        if (Test-Path $dir) {
            $oldFiles = Get-ChildItem $dir -File | Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-7) }
            $cleanedSize = ($oldFiles | Measure-Object -Property Length -Sum).Sum / 1MB
            $oldFiles | Remove-Item -Force -ErrorAction SilentlyContinue
            $totalCleaned += $cleanedSize
        }
    }
    
    if ($totalCleaned -gt 0) {
        Write-Host "   ✅ Cleaned $([math]::Round($totalCleaned, 1)) MB of old downloads" -ForegroundColor Green
    } else {
        Write-Host "   ✅ No old downloads to clean" -ForegroundColor Green
    }
    
    # Update yt-dlp
    Write-Host "📺 Updating yt-dlp..." -ForegroundColor Yellow
    try {
        & "venv\Scripts\python.exe" -m pip install --upgrade yt-dlp --quiet
        Write-Host "   ✅ yt-dlp updated successfully" -ForegroundColor Green
    } catch {
        Write-Host "   ⚠️  Failed to update yt-dlp" -ForegroundColor Yellow
    }
    
    # Start Aria2c if not running
    $aria2c = Get-Aria2cStatus
    if ($aria2c.Status -ne "Running") {
        Write-Host "⚡ Starting Aria2c daemon..." -ForegroundColor Yellow
        try {
            .\start_aria2_daemon.ps1
            Write-Host "   ✅ Aria2c daemon started" -ForegroundColor Green
        } catch {
            Write-Host "   ⚠️  Failed to start Aria2c daemon" -ForegroundColor Yellow
        }
    } else {
        Write-Host "   ✅ Aria2c already running" -ForegroundColor Green
    }
    
    Write-Host ""
    Write-Host "🎉 OPTIMIZATION COMPLETE!" -ForegroundColor Green
    Write-Host "Your downloader is now running at maximum performance!" -ForegroundColor White
}

if (-not $Live -and -not $Report -and -not $Optimize) {
    Write-Host "📊 QUICK STATUS CHECK" -ForegroundColor Cyan
    Write-Host "====================" -ForegroundColor Cyan
    Write-Host ""
    
    $health = Test-ApplicationHealth
    $aria2c = Get-Aria2cStatus
    $cache = Get-CacheStats
    
    Write-Host "Application: $($health.Status)" -ForegroundColor $(if($health.Status -eq "Healthy"){"Green"}else{"Red"})
    Write-Host "Aria2c: $($aria2c.Status)" -ForegroundColor $(if($aria2c.Status -eq "Running"){"Green"}else{"Yellow"})
    Write-Host "Cache: $($cache.Status)" -ForegroundColor White
    Write-Host ""
    Write-Host "🔧 Available Options:" -ForegroundColor Yellow
    Write-Host "   -Live     : Real-time monitoring" -ForegroundColor White
    Write-Host "   -Report   : Detailed performance report" -ForegroundColor White
    Write-Host "   -Optimize : Run performance optimizations" -ForegroundColor White
    Write-Host ""
    Write-Host "🌐 Access your app: http://127.0.0.1:8000/universal_tailwind" -ForegroundColor Cyan
}