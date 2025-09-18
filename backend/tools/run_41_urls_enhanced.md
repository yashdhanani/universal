# Enhanced 41-URL Test

This script tests the unified `/api/info` endpoint for 41 URLs across multiple platforms.

## Features
- Auto `multi=1` for YouTube playlists/channels/@user and Instagram posts/profiles.
- Per-platform timeouts and retries with exponential backoff.
- Concurrent requests (default 6).
- JSON report output: `tools/reports/run_41_urls_enhanced.json`.

## Usage

### Activate venv and run manually
```powershell
Set-Location e:\project\downloader
.\venv\Scripts\activate
python -m uvicorn main_api:APP --host 127.0.0.1 --port 8004
python tools/run_41_urls_enhanced.py --concurrency 6
```

### One-command runner (recommended)
```powershell
powershell -ExecutionPolicy Bypass -File e:\project\downloader\tools\run_41_urls_enhanced.ps1
```
- Ensures port 8004 is free (kills any process bound to it), starts the API, then runs the test.
- Respects environment variables (see below) and INFO_CONCURRENCY.

### Environment variables
- COOKIES_FILE — optional, path to Netscape-format cookies for restricted platforms.
- INFO_BASE — override default API base URL.
- INFO_OUTFILE — override default JSON output file.
- INFO_TIMEOUT, INFO_PUBLIC_TIMEOUT, INFO_RESTRICTED_TIMEOUT — per-platform timeouts.
- INFO_RETRIES, INFO_RETRY_BACKOFF — retry policy for transient errors.
- INFO_CONCURRENCY — number of parallel requests (default 6).