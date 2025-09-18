Param(
  [int]$ApiPort = 5000
)

$Root = "e:\project\downloader"
$Uvicorn = Join-Path $Root "venv\Scripts\uvicorn.exe"

Write-Host "Starting backend (single-frontend mode) on http://127.0.0.1:$ApiPort ..."
$backendJob = Start-Job -Name "backend" -ScriptBlock {
  param($Uvicorn, $Root, $ApiPort)
  Set-Location $Root
  & $Uvicorn "main_api:APP" --host 127.0.0.1 --port $ApiPort --reload 2>&1
} -ArgumentList $Uvicorn, $Root, $ApiPort

Write-Host ""
Write-Host "Open http://127.0.0.1:$ApiPort/universal_tailwind"
Write-Host ""

Write-Host "Streaming logs. Press Ctrl+C to stop."
try {
  Receive-Job -Id $backendJob.Id -Wait
} finally {
  Write-Host ""
  Write-Host "Stopping backend..."
  Get-Job -Name backend | Stop-Job -PassThru | Remove-Job | Out-Null
}