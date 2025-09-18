Param(
  [int]$ApiPort = 4040,
  [int]$TimeoutSeconds = 45,
  [switch]$Quiet
)

$deadline = (Get-Date).AddSeconds($TimeoutSeconds)
$uri = "http://localhost:$ApiPort/api/tunnels"

if (-not $Quiet) { Write-Host "Waiting for ngrok inspector on $uri ..." }

$publicUrl = $null
while (-not $publicUrl -and (Get-Date) -lt $deadline) {
  try {
    $resp = Invoke-RestMethod -Method GET -Uri $uri -TimeoutSec 5
    if ($resp -and $resp.tunnels) {
      $https = $resp.tunnels | Where-Object { $_.proto -eq 'https' } | Select-Object -First 1
      if ($https -and $https.public_url) { $publicUrl = $https.public_url; break }
    }
  } catch { Start-Sleep -Milliseconds 500 }
  Start-Sleep -Milliseconds 500
}

if ($publicUrl) {
  if (-not $Quiet) {
    Write-Host "✅ ngrok public URL:" -ForegroundColor Green
    Write-Host $publicUrl -ForegroundColor Cyan
    Write-Output $publicUrl | Set-Clipboard 2>$null
    Write-Host "(Copied to clipboard)"
  }
  # Always write plain URL to stdout so callers can capture it
  Write-Output $publicUrl
  exit 0
} else {
  Write-Error "Failed to discover ngrok URL within $TimeoutSeconds seconds. Is ngrok running and port $ApiPort open?"
  exit 1
}