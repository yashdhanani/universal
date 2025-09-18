# Test all platforms against local API
# Prerequisites: backend running at http://127.0.0.1:8000 and ffmpeg installed

$ApiBase = "http://127.0.0.1:8000"

# Provide at least one public URL per platform.
# Replace placeholders with real public links before running.
$Tests = @(
    @{ Platform = 'youtube';   Url = 'https://www.youtube.com/watch?v=BaW_jenozKc';           Labels = @('video','mp4','mp3') },
    @{ Platform = 'youtube';   Url = 'https://www.youtube.com/shorts/REPLACE';               Labels = @('shorts','mp4','mp3') },
    @{ Platform = 'instagram'; Url = 'https://www.instagram.com/p/REPLACE/';                 Labels = @('mp4','jpg','mp3') },
    @{ Platform = 'facebook';  Url = 'https://www.facebook.com/REPLACE/videos/REPLACE/';     Labels = @('mp4') },
    @{ Platform = 'tiktok';    Url = 'https://www.tiktok.com/@REPLACE/video/REPLACE';        Labels = @('mp4','mp3') },
    @{ Platform = 'twitter';   Url = 'https://twitter.com/REPLACE/status/REPLACE';           Labels = @('mp4','mp3') },
    @{ Platform = 'pinterest'; Url = 'https://www.pinterest.com/pin/REPLACE/';               Labels = @('mp4','jpg','mp3') },
    @{ Platform = 'snapchat';  Url = 'https://www.snapchat.com/add/REPLACE';                 Labels = @('mp4') },
    @{ Platform = 'linkedin';  Url = 'https://www.linkedin.com/posts/REPLACE';               Labels = @('mp4') },
    @{ Platform = 'reddit';    Url = 'https://www.reddit.com/r/REPLACE/comments/REPLACE/';   Labels = @('mp4','mp3') }
)

Function Invoke-Api {
    param(
        [string]$Method,
        [string]$Url
    )
    try {
        if ($Method -eq 'HEAD') {
            $resp = Invoke-WebRequest -UseBasicParsing -Method Head -Uri $Url -TimeoutSec 25 -MaximumRedirection 0 -ErrorAction Stop
            return @{ ok = $true; status = $resp.StatusCode; url = $Url }
        } else {
            $resp = Invoke-WebRequest -UseBasicParsing -Method Get -Uri $Url -TimeoutSec 60 -ErrorAction Stop
            return @{ ok = $true; status = $resp.StatusCode; content = $resp.Content; url = $Url }
        }
    } catch {
        return @{ ok = $false; error = $_.Exception.Message; url = $Url }
    }
}

$Results = @()

foreach ($t in $Tests) {
    $platform = $t.Platform
    $url = $t.Url
    if ($url -match 'REPLACE') { continue }
    $enc = [System.Web.HttpUtility]::UrlEncode($url)

    Write-Host "\n=== $platform ==="

    # 1) Analyze
    $analyzeUrl = "$ApiBase/api/v2/$platform/info?url=$enc"
    $r1 = Invoke-Api -Method GET -Url $analyzeUrl
    $Results += @{ platform=$platform; step='analyze'; ok=$r1.ok; status=$r1.status; url=$analyzeUrl; error=$r1.error }
    if (-not $r1.ok) { Write-Host "Analyze failed: $($r1.error)" -ForegroundColor Red; continue }

    # 2) Instant MP4 (best)
    $mp4Url = "$ApiBase/api/v2/$platform/instant?url=$enc&format_id=best"
    $r2 = Invoke-Api -Method HEAD -Url $mp4Url  # do HEAD to check availability
    $Results += @{ platform=$platform; step='instant_mp4'; ok=$r2.ok; status=$r2.status; url=$mp4Url; error=$r2.error }

    # 3) Instant MP3 (192)
    $mp3Url = "$ApiBase/api/v2/$platform/instant?url=$enc&format_id=mp3_192"
    $r3 = Invoke-Api -Method HEAD -Url $mp3Url
    $Results += @{ platform=$platform; step='instant_mp3'; ok=$r3.ok; status=$r3.status; url=$mp3Url; error=$r3.error }
}

# Summary
"\n--- SUMMARY ---"
$Results | ForEach-Object {
    if ($_.ok) {
        Write-Host ("[OK] {0} / {1} -> {2}" -f $_.platform, $_.step, $_.status) -ForegroundColor Green
    } else {
        Write-Host ("[FAIL] {0} / {1} -> {2}" -f $_.platform, $_.step, $_.error) -ForegroundColor Yellow
    }
}

# Save JSON report
$Out = $Results | ConvertTo-Json -Depth 5
$ReportPath = Join-Path (Split-Path $MyInvocation.MyCommand.Path) 'test_all_platforms.report.json'
$Out | Out-File -Encoding utf8 $ReportPath
Write-Host "\nReport saved to: $ReportPath"