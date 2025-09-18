# Extract inline JavaScript from frontend/index.html into frontend/static/js/universal.js
# and update index.html to reference it

$ErrorActionPreference = 'Stop'

$root = "e:\project\downloader"
$htmlPath = Join-Path $root "frontend\index.html"
$jsDir = Join-Path $root "frontend\static\js"
$jsPath = Join-Path $jsDir "universal.js"

if (!(Test-Path $htmlPath)) { throw "HTML not found: $htmlPath" }
if (!(Test-Path $jsDir)) { New-Item -ItemType Directory -Force -Path $jsDir | Out-Null }

$content = Get-Content -Path $htmlPath -Raw

# Find inline <script> ... </script> that contains window.progressManager
$regex = [regex]'(?is)<script>(.*?)</script>'
$matches = $regex.Matches($content)
if ($matches.Count -eq 0) { throw "No inline <script> block found." }

$targetMatch = $null
foreach ($m in $matches) {
  $body = $m.Groups[1].Value
  if ($body -match 'window\.progressManager') { $targetMatch = $m; break }
}
if ($null -eq $targetMatch) { throw "Could not find the app inline script (window.progressManager)" }

$js = $targetMatch.Groups[1].Value.Trim()

# Write JS file
Set-Content -Path $jsPath -Value $js -Encoding UTF8

# Replace inline block with external reference
$scriptTag = '<script src="/static/js/universal.js"></script>'
$startIdx = $targetMatch.Index
$length = $targetMatch.Length
$updated = $content.Remove($startIdx, $length).Insert($startIdx, $scriptTag)

Set-Content -Path $htmlPath -Value $updated -Encoding UTF8

Write-Host "Extracted JS to: $jsPath"
Write-Host "Updated HTML to reference: $scriptTag"