Param(
  [switch]$Build,
  [switch]$WithTunnel,
  [string]$NgrokToken,
  [string]$Origins
)

$Root = "e:\project\downloader"
Set-Location $Root

if ($WithTunnel) {
  if (-not $NgrokToken) {
    Write-Error "Provide -NgrokToken when using -WithTunnel"; exit 1
  }
  $env:NGROK_AUTHTOKEN = $NgrokToken
}

$profileArgs = @()
if ($WithTunnel) { $profileArgs += @("--profile", "tunnel") }

if ($Build) {
  docker compose @profileArgs up --build -d
} else {
  docker compose @profileArgs up -d
}