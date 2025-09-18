Param(
  [Parameter(Mandatory = $true)][string]$NgrokToken,
  [switch]$Build,
  [int]$WaitSeconds = 45,
  [switch]$AutoCors,
  [string]$Origins
)

$Root = "e:\project\downloader"
$PrintScript = Join-Path $Root "print_ngrok_url.ps1"

function Fail($msg) {
  Write-Error $msg
  exit 1
}

# Basic checks
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
  Fail "Docker is not installed or not in PATH. Install Docker Desktop and retry."
}

if (-not (Test-Path $PrintScript)) {
  Fail "Helper not found: $PrintScript"
}

# Export token for this session so compose picks it up
$env:NGROK_AUTHTOKEN = $NgrokToken

Write-Host "Starting Docker stack (with ngrok sidecar)..." -ForegroundColor Cyan
try {
  Set-Location $Root
  if ($Build) {
    docker compose --profile tunnel up --build -d
  } else {
    docker compose --profile tunnel up -d
  }
} catch {
  Fail "Failed to start docker compose: $($_.Exception.Message)"
}

Write-Host "Waiting for ngrok to initialize (up to $WaitSeconds seconds)..."
$ngrokUrl = $null
try {
  $ngrokUrl = & $PrintScript -ApiPort 4040 -TimeoutSeconds $WaitSeconds -Quiet
  if ($LASTEXITCODE -ne 0) { $ngrokUrl = $null }
} catch {
  Write-Warning "Could not retrieve ngrok URL: $($_.Exception.Message)"
}

if ($ngrokUrl) {
  Write-Host "✅ ngrok public URL: $ngrokUrl" -ForegroundColor Green
  $finalOrigins = if ([string]::IsNullOrWhiteSpace($Origins)) { $ngrokUrl } else { "$Origins,$ngrokUrl" }
  if ($AutoCors) {
    Write-Host "Setting CORS_ALLOW_ORIGINS to: $finalOrigins and restarting API service..." -ForegroundColor Yellow
    $env:CORS_ALLOW_ORIGINS = $finalOrigins
    # Recreate only the api service so env propagates
    docker compose up -d --no-deps --build api | Out-Null
  } else {
    Write-Host "To allow browser apps, set CORS_ALLOW_ORIGINS in .env and restart:"
    Write-Host "  CORS_ALLOW_ORIGINS=$finalOrigins"
    Write-Host "  docker compose up -d"
  }
} else {
  Write-Warning "ngrok URL not detected. Check http://localhost:4040"
}

# Helpful next steps
Write-Host ""; Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1) Pass X-API-Key for protected endpoints."
Write-Host "2) Inspect requests at: http://localhost:4040"