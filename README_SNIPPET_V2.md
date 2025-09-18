# Universal Media Downloader – v2 API Quick Guide

## URLs to open
- Dev (Flask): http://127.0.0.1:5000/universal_tailwind
- ASGI (FastAPI): http://127.0.0.1:8000/universal_tailwind
- Root `/` redirects to `/universal_tailwind`.

## Core endpoints
- Analyze: GET `/api/v2/{platform}/info?url=...`
- Start download (server): POST `/api/v2/{platform}/download` -> `{ task_id }`
- Task progress: GET `/api/v2/task/{task_id}`
- Cancel task: DELETE `/api/v2/task/{task_id}`
- Final file: GET `/download/{filename}`
- Instant download (no server processing):
  - Sign: GET `/api/v2/sign?url=...&format_id=...&filename=...` -> `{ token, dl }`
  - Resolve: GET `/dl?token=...` (or use returned `dl`)
- Passthrough proxy (images/direct media): GET `/api/passthrough?url=...&filename=...`

## Platforms supported
YouTube, Instagram, Facebook (instant only), TikTok, Twitter/X, Pinterest, LinkedIn, Reddit, Snapchat.

## Accepted URL formats
- YouTube: `https://www.youtube.com/watch?v=ID`, `https://youtu.be/ID`, `https://www.youtube.com/shorts/ID`
- Instagram: `/p/ID/`, `/reel/ID/`, `/tv/ID/`, `/stories/USER/ID/`
- Facebook: `.../videos/ID/`, `https://fb.watch/ID/`
- TikTok: `https://www.tiktok.com/@user/video/ID`, `https://vm.tiktok.com/SHORT_ID`
- Twitter/X: `https://twitter.com/USER/status/ID`, `https://x.com/USER/status/ID`
- Pinterest: `https://www.pinterest.com/pin/ID/`, `https://pin.it/SHORT_ID`
- LinkedIn: `/feed/update/urn:li:activity:ID`, `/posts/ID`
- Reddit: `https://www.reddit.com/r/SUB/comments/POST_ID/...`, `https://v.redd.it/VIDEO_ID`
- Snapchat: `https://story.snapchat.com/s/ID`

## Demo calls
- Analyze: `/api/v2/youtube/info?url=https://www.youtube.com/watch?v=dQw4w9WgXcQ`
- Start download JSON: `{ "url": "https://...", "format_id": "best" }`
- Poll: `/api/v2/task/{task_id}`
- Cancel: `DELETE /api/v2/task/{task_id}`
- Instant: `/api/v2/sign?url=...&format_id=best` => open returned `dl` URL

## Notes
- Facebook server-download is disabled; use instant (sign/passthrough).
- Cookies Manager page: `/cookies`; APIs under `/api/auth/cookies/*`.