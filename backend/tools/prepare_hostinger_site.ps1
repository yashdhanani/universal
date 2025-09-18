# Prepares a Hostinger-ready static site from templates/universal_tailwind.html
# - Copies /static to /hostinger_site/static
# - Copies universal_tailwind.html to /hostinger_site/index.html
# - Removes Jinja blocks ({% if ... %} ... {% endif %})
# - Switches Tailwind to local CSS
# - Ensures config.js is loaded (already referenced in head)

$ErrorActionPreference = 'Stop'

$root = "e:\project\downloader"
$srcHtml = Join-Path $root "templates\universal_tailwind.html"
$destDir = Join-Path $root "hostinger_site"
$destHtml = Join-Path $destDir "index.html"
$srcStatic = Join-Path $root "static"
$destStatic = Join-Path $destDir "static"

# Create destination directory
if (-not (Test-Path $destDir)) { New-Item -ItemType Directory -Path $destDir | Out-Null }

# Copy static assets
if (Test-Path $destStatic) { Remove-Item -Recurse -Force $destStatic }
Copy-Item -Path $srcStatic -Destination $destStatic -Recurse -Force

# Copy HTML
Copy-Item -Path $srcHtml -Destination $destHtml -Force

# Read and transform HTML content (force UTF-8 to preserve emojis)
$content = Get-Content -Path $destHtml -Raw -Encoding utf8

# 1) Remove Jinja blocks: {% if ... %} ... {% endif %}
# (?s) enables singleline (dotall) mode
$content = [Regex]::Replace($content, "(?s)\{\%\s*if.*?\%\}.*?\{\%\s*endif\s*\%\}", "")

# 2) Switch Tailwind to local CSS (comment out CDN, enable local link)
$content = $content -replace '<script src="https://cdn.tailwindcss.com"></script>', '<!-- Tailwind CDN removed for Hostinger -->'
$content = $content -replace '<!--\s*<link href="/static/tailwind.min.css" rel="stylesheet">\s*-->', '<link href="/static/tailwind.min.css" rel="stylesheet">'

# 3) Ensure config.js is referenced (added earlier, but keep idempotent)
if ($content -notmatch '/static/config.js') {
  $replacement = @"
  <script src="/static/config.js"></script>
</head>
"@
  $content = [Regex]::Replace($content, '(?i)</head>', $replacement)
}

# 4) Optional: ensure API_BASE reads runtime config (already updated in template)
# No change needed if present.

# Write back
Set-Content -Path $destHtml -Value $content -Encoding UTF8

Write-Host "Hostinger static site prepared at: $destDir"
Write-Host "Upload contents of '$destDir' to Hostinger public_html"