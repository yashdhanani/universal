# Project: YouTube Downloader (Flask + yt-dlp)

## Overview
- A Flask web app to analyze and download YouTube videos with progress UI.
- Frontend: vanilla JS (templates/index.html). Backend: Flask (app.py), uses yt-dlp.
- Downloads saved to downloads/; logs in logs/app.log.

## Key Files
- app.py: Main Flask app, routes, yt-dlp integration, progress tracking.
- templates/index.html: Main UI for YouTube downloads.
- templates/universal.html: Alternate UI (WIP) for multi-platform.
- static/: Styles, manifest, service worker.
- config.py: Configuration classes.
- start_development.bat / start_production*.bat: Windows start scripts.
- requirements.txt: Python dependencies.

## Important Endpoints
- POST /api/video_info: Analyze a YouTube URL and return available formats (deduplicated and filtered).
- POST /api/download: Start a download task for selected format; returns task_id.
- GET  /api/progress/<task_id>: Poll current task status and progress text.
- GET  /download/<filename>: Download produced file.
- POST /api/<platform>/analyze: Analyze by platform (YouTube implemented; others WIP).
- POST /api/<platform>/download: Download by platform (YouTube implemented).
- GET  /api/debug_formats/<video_id>: Dump raw formats for debugging.
- GET  /clear_downloads: Remove files in downloads/.

## Download Flow (YouTube)
1. Frontend calls /api/video_info with URL; backend merges formats from multiple clients (android/ios/web), filters HLS/premium/storyboard, deduplicates by resolution+fps+codec+ext, estimates size when needed.
2. User selects a format (or Best). UI posts to /api/download with url + format_id.
3. Backend chooses appropriate format selector (merge bestaudio when video-only), sets outtmpl, monitors progress via hooks, and merges to MKV when needed.
4. After download, backend picks the newest file containing the video ID from downloads/ and marks task finished.
5. Frontend polls /api/progress/<task_id> and then shows /download/<filename> link.

## Environment Variables
- FFMPEG_LOCATION or FFMPEG_PATH: Absolute path to ffmpeg binary/folder (recommended to ensure merging works).
- COOKIES_FILE: Path to cookies.txt for YouTube (helps bypass consent/age walls or 403).
- ARIA2C_PATH: Path to aria2c; when present, enables external downloader for faster IO.

## Known Behaviors / Tips
- High resolutions (e.g., 2160p) are often VP9/AV1; merging produces MKV to preserve quality. MP4 at very high resolutions may be unavailable.
- If you see “Requested format is not available”, choose a different format or use Best. MP4/H.264 generally available up to 1080p.
- 403/consent issues: provide COOKIES_FILE.
- Progress stuck at Processing previously caused by filename detection; fixed by scanning newest file by video ID.

## Running Locally
- Windows (dev):
  1) Ensure Python 3.10+ and ffmpeg installed.
  2) pip install -r requirements.txt
  3) set FFMPEG_LOCATION=C:\\path\\to\\ffmpeg (optional but recommended)
  4) python app.py (or run start_development.bat)
- App listens on http://127.0.0.1:5000

## Logs & Downloads
- Logs: logs/app.log (rotating). Adjust logger in app.py if needed.
- Output: downloads/ (named with title, id, and sometimes format_id; merges prefer MKV).

## Troubleshooting
- Missing file after success: verify ffmpeg path and write permissions to downloads/.
- Few formats or 403: add COOKIES_FILE from browser export; retry.
- Slow downloads: install aria2c and set ARIA2C_PATH.

## Dependencies
- Flask, yt-dlp, its dependencies as per requirements.txt.