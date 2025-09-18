# Universal Downloader — Test Links (Local)

Use these to manually test each platform on your local backend.

- **API base**: http://127.0.0.1:8000
- Replace `PASTE_ENCODED_URL` with the percent-encoded media URL.
- Suggested: open Analyze first, then try Instant MP4 and Instant MP3.

## Platforms and endpoints
For each platform: youtube, instagram, facebook, tiktok, twitter, pinterest, snapchat, linkedin, reddit

- **Analyze**:
  - GET `http://127.0.0.1:8000/api/v2/{platform}/info?url=PASTE_ENCODED_URL`
- **Instant MP4 (best)**:
  - GET `http://127.0.0.1:8000/api/v2/{platform}/instant?url=PASTE_ENCODED_URL&format_id=best`
- **Instant MP3 (192 kbps)**:
  - GET `http://127.0.0.1:8000/api/v2/{platform}/instant?url=PASTE_ENCODED_URL&format_id=mp3_192`

Notes:
- **Facebook** server-side task is disabled by design; use Instant only.
- **Instagram/LinkedIn/Snapchat** may require cookies for some URLs. Use public posts.

## Sample URLs (public)
- **YouTube (video)**: https://www.youtube.com/watch?v=BaW_jenozKc
- **YouTube Shorts (replace)**: https://www.youtube.com/shorts/REPLACE
- **Instagram (public post, replace)**: https://www.instagram.com/p/REPLACE/
- **Facebook (public video, replace)**: https://www.facebook.com/REPLACE/videos/REPLACE/
- **TikTok (public video, replace)**: https://www.tiktok.com/@REPLACE/video/REPLACE
- **Twitter/X (public tweet with video, replace)**: https://twitter.com/REPLACE/status/REPLACE
- **Pinterest (pin, replace)**: https://www.pinterest.com/pin/REPLACE/
- **Snapchat (public spotlight, replace)**: https://www.snapchat.com/add/REPLACE or spotlight link
- **LinkedIn (public post, replace)**: https://www.linkedin.com/posts/REPLACE
- **Reddit (public post with video, replace)**: https://www.reddit.com/r/REPLACE/comments/REPLACE/

Tip: URL-encode quickly by pasting into your browser’s address bar encoder or using an online encoder.