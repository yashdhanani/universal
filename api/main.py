"""
Multi-platform video downloader API.
Supports YouTube, Instagram, Facebook, TikTok, Twitter, Pinterest.
"""
from fastapi import FastAPI, Query, HTTPException, BackgroundTasks, Request, Body
from fastapi.responses import JSONResponse, StreamingResponse, RedirectResponse, HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import requests
import os
import logging
from typing import Optional, Dict, Any, Iterator
import tempfile
from pathlib import Path
import time, json, hmac, hashlib, base64
from urllib.parse import urlencode, quote, unquote
from celery.result import AsyncResult
from backend.tasks.universal_download import universal_download_task
from backend.tasks.celery_app import celery

# Load environment variables from .env for cookies, ffmpeg, etc.
try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path="e:\\project\\downloader\\.env")
except Exception:
    pass

# Import platform modules
from backend.youtube import youtube_info, youtube_download, get_quality_options as youtube_quality_options
from backend.instagram import instagram_info, instagram_download, get_quality_options as instagram_quality_options
from backend.facebook import facebook_info, facebook_download, get_quality_options as facebook_quality_options
from backend.tiktok import tiktok_info, tiktok_download, get_quality_options as tiktok_quality_options
from backend.twitter import twitter_info, twitter_download, get_quality_options as twitter_quality_options
from backend.pinterest import pinterest_info, pinterest_download, get_quality_options as pinterest_quality_options
from backend.platforms.naver import analyze as naver_info, prepare_download as naver_download
from backend.utils import detect_platform, sanitize_filename, format_filesize, get_content_type, clean_title
from backend.downloader import cleanup_temp_file

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Multi-Platform Video Downloader API",
    description="Download videos from YouTube, Instagram, Facebook, TikTok, Twitter, Pinterest",
    version="2.0.0"
)

# Simple SEO-friendly landing redirects
LANDING_ROUTES = {
    "/youtube-downloader": "/frontend/youtube-downloader.html",
    "/instagram-downloader": "/frontend/instagram-downloader.html",
    "/facebook-video-downloader": "/frontend/facebook-video-downloader.html",
    "/tiktok-downloader": "/frontend/tiktok-downloader.html",
    "/twitter-video-downloader": "/frontend/twitter-video-downloader.html",
    "/pinterest-downloader": "/frontend/pinterest-downloader.html",
}

for src, dst in LANDING_ROUTES.items():
    @app.get(src, include_in_schema=False)
    async def _redir(dst=dst):  # type: ignore
        return RedirectResponse(url=dst, status_code=302)

# Serve robots.txt and sitemap.xml from API as well
@app.get("/robots.txt", include_in_schema=False)
async def robots_txt():
    base = os.environ.get("CANONICAL_BASE_URL", "https://medidown.com").rstrip("/")
    content = f"User-agent: *\nAllow: /\n\nSitemap: {base}/sitemap.xml\n"
    return HTMLResponse(content, media_type="text/plain")

@app.get("/sitemap.xml", include_in_schema=False)
async def sitemap_xml():
    base = os.environ.get("CANONICAL_BASE_URL", "https://medidown.com").rstrip("/")
    pages = [f"{base}/", f"{base}/index.html"] + [f"{base}{path}" for path in LANDING_ROUTES.keys()]
    xml_body = "<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">" + "".join([f"<url><loc>{u}</loc></url>" for u in pages]) + "</urlset>"
    xml = f"<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n{xml_body}\n"
    return HTMLResponse(xml, media_type="application/xml")

@app.get("/sitemap_index.xml", include_in_schema=False)
async def sitemap_index():
    base = os.environ.get("CANONICAL_BASE_URL", "https://medidown.com").rstrip("/")
    body = f"<sitemapindex xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">" \
           f"<sitemap><loc>{base}/sitemap.xml</loc></sitemap>" \
           f"</sitemapindex>"
    xml = f"<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n{body}\n"
    return HTMLResponse(xml, media_type="application/xml")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Platform handlers mapping
PLATFORM_HANDLERS = {
    "youtube": {
        "info": youtube_info,
        "download": youtube_download,
        "quality_options": youtube_quality_options,
    },
    "instagram": {
        "info": instagram_info,
        "download": instagram_download,
        "quality_options": instagram_quality_options,
    },
    "facebook": {
        "info": facebook_info,
        "download": facebook_download,
        "quality_options": facebook_quality_options,
    },
    "tiktok": {
        "info": tiktok_info,
        "download": tiktok_download,
        "quality_options": tiktok_quality_options,
    },
    "twitter": {
        "info": twitter_info,
        "download": twitter_download,
        "quality_options": twitter_quality_options,
    },
    "pinterest": {
        "info": pinterest_info,
        "download": pinterest_download,
        "quality_options": pinterest_quality_options,
    },
    "naver": {
        "info": naver_info,
        "download": naver_download,
    },
}

@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok", "version": "2.0.0"}

@app.get("/platforms")
def list_platforms():
    """List supported platforms."""
    return {
        "platforms": list(PLATFORM_HANDLERS.keys()),
        "count": len(PLATFORM_HANDLERS)
    }

@app.get("/detect")
def detect_url_platform(url: str = Query(..., description="URL to analyze")):
    """Detect which platform a URL belongs to."""
    platform = detect_platform(url)
    if not platform:
        raise HTTPException(status_code=400, detail="Unsupported or invalid URL")
    
    return {
        "url": url,
        "platform": platform,
        "supported": platform in PLATFORM_HANDLERS
    }

# Generic platform endpoints
@app.get("/{platform}/info")
async def get_platform_info(platform: str, url: str = Query(...)):
    """Get video information for any supported platform.
    Auto-corrects platform based on the URL so pasting a YouTube link into Instagram works.
    """
    # Auto-detect platform from URL and prefer detected when supported
    try:
        from backend.tasks.universal_download import _detect_platform as _ud_detect
        detected = _ud_detect(url)
        if detected in PLATFORM_HANDLERS and detected != platform:
            platform = detected
    except Exception:
        pass

    if platform not in PLATFORM_HANDLERS:
        raise HTTPException(status_code=404, detail=f"Platform '{platform}' not supported")
    
    try:
        handler = PLATFORM_HANDLERS[platform]
        info = handler["info"](url)
        
        # Add quality options for better UX
        if isinstance(info, dict) and "formats" in info and handler.get("quality_options"):
            info["quality_options"] = handler["quality_options"](info["formats"])
        
        # Clean up the response
        if isinstance(info, dict):
            info["title"] = clean_title(info.get("title", ""))
        
        return info
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting {platform} info for {url}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get video information: {str(e)}")

# v2 aliases
@app.get("/api/v2/{platform}/info")
async def v2_get_platform_info(platform: str, url: str = Query(...)):
    return await get_platform_info(platform, url)

@app.post("/api/v2/{platform}/download")
async def v2_start_download(platform: str, payload: dict = Body(...)):
    url = payload.get("url")
    format_id = payload.get("format_id", "best")
    if not url:
        raise HTTPException(status_code=400, detail="Missing url")
    try:
        # Enqueue Celery universal task (Facebook is rejected inside the task)
        res = universal_download_task.apply_async(args=[url, format_id, platform])
        return {"task_id": res.id, "state": "PENDING"}
    except Exception as e:
        logger.error(f"v2 start download failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to start download")

@app.get("/api/v2/task/{task_id}")
async def v2_task_status(task_id: str):
    try:
        # Prefer Redis progress
        from backend.tasks.progress import get_progress  # type: ignore
        data = get_progress(task_id)
        if data:
            return {"task_id": task_id, "state": (data.get("status") or "PROGRESS").upper(), **data}
    except Exception:
        pass
    # Fall back to Celery state
    try:
        ar = AsyncResult(task_id, app=celery)
        state = (ar.state or "PENDING").upper()
        info = ar.info if isinstance(ar.info, dict) else ({"detail": str(ar.info)} if ar.info else {})
        payload = {"task_id": task_id, "state": state, **info}
        # Normalize fields for frontend expectations
        if state == "SUCCESS":
            payload.setdefault("status", "finished")
            if "filename" in info:
                payload["filename"] = info["filename"]
        elif state == "FAILURE":
            payload.setdefault("status", "error")
            if "error" not in payload and "detail" in payload:
                payload["error"] = payload["detail"]
        return payload
    except Exception:
        return {"task_id": task_id, "state": "PENDING"}

@app.delete("/api/v2/task/{task_id}")
async def v2_task_cancel(task_id: str):
    try:
        ar = AsyncResult(task_id, app=celery)
        ar.revoke(terminate=True)
        return {"status": "cancelled"}
    except Exception:
        return {"status": "cancelled"}

# Explicit instant (stream/proxy) endpoint for v2
@app.get("/api/v2/{platform}/instant")
@app.head("/api/v2/{platform}/instant")
async def v2_instant_download(
    platform: str,
    url: str = Query(...),
    format_id: str = Query("best"),
    filename: Optional[str] = Query(None),
    background_tasks: BackgroundTasks = None,
    request: Request = None,
):
    """Instant download via streaming/proxy for any supported platform.
    This reuses the same logic as /{platform}/download but under the v2 namespace.
    """
    return await download_from_platform(platform, url, format_id, filename, background_tasks, request)

# Convenience aliases to mirror /{platform}/download for instant streaming
@app.get("/{platform}/instant")
@app.head("/{platform}/instant")
async def instant_download_alias(
    platform: str,
    url: str = Query(...),
    format_id: str = Query("best"),
    filename: Optional[str] = Query(None),
    background_tasks: BackgroundTasks = None,
    request: Request = None,
):
    return await download_from_platform(platform, url, format_id, filename, background_tasks, request)

@app.get("/{platform}/download")
@app.head("/{platform}/download")
async def download_from_platform(
    platform: str,
    url: str = Query(...),
    format_id: str = Query("best", description="Format ID to download"),
    filename: Optional[str] = Query(None, description="Custom filename"),
    background_tasks: BackgroundTasks = None,
    request: Request = None,
    fast: Optional[bool] = Query(False, description="If true and URL is direct, prefer 3xx redirect for maximum speed"),
    proxy: Optional[bool] = Query(False, description="Force server proxy even if direct URL available")
):
    """Download video from any supported platform.
    Auto-corrects platform based on the URL so pasting a YouTube link into Instagram works.
    """
    # Auto-detect platform from URL and prefer detected when supported
    try:
        from backend.tasks.universal_download import _detect_platform as _ud_detect
        detected = _ud_detect(url)
        if detected in PLATFORM_HANDLERS and detected != platform:
            platform = detected
    except Exception:
        pass

    if platform not in PLATFORM_HANDLERS:
        raise HTTPException(status_code=404, detail=f"Platform '{platform}' not supported")
    
    try:
        handler = PLATFORM_HANDLERS[platform]
        file_or_url, info, needs_cleanup = handler["download"](url, format_id)
        
        # Determine filename
        if not filename:
            title = clean_title(info.get("title", "video"))
            # Pick default extension by format_id (mp3_* => .mp3, else .mp4)
            default_ext = "mp3" if str(format_id).lower().startswith("mp3_") else "mp4"
            filename = sanitize_filename(f"{title}.{default_ext}")
        
        # Determine content type
        if needs_cleanup:
            # It's a local file (merged or audio-extracted)
            # Infer content type from the output file extension
            ext = os.path.splitext(filename)[1].lstrip(".") or "mp4"
            content_type = get_content_type(ext)
            
            def iterfile():
                try:
                    with open(file_or_url, "rb") as f:
                        # Use larger chunks to reduce overhead and speed up transfers
                        chunk_size = max(8192, int(os.environ.get("STREAM_CHUNK_SIZE", 1024 * 256)))
                        while chunk := f.read(chunk_size):
                            yield chunk
                finally:
                    # Schedule post-download hooks and cleanup
                    if background_tasks:
                        try:
                            from backend.utils.post_download import run_post_download
                            meta = {
                                "success": True,
                                "path": file_or_url,
                                "filename": os.path.basename(file_or_url),
                                "platform": platform,
                                "url": url,
                                "title": info.get("title"),
                                "uploader": info.get("uploader"),
                                "ext": os.path.splitext(file_or_url)[1].lstrip("."),
                                "thumbnail": info.get("thumbnail") or info.get("thumbnail_url"),
                                "format_id": format_id,
                            }
                                
                            background_tasks.add_task(run_post_download, meta, True, None)
                        except Exception:
                            pass
                        background_tasks.add_task(cleanup_temp_file, file_or_url)
            
            return StreamingResponse(
                iterfile(),
                media_type=content_type,
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}"',
                    "Cache-Control": "no-cache",
                    "Content-Length": str(os.path.getsize(file_or_url)),
                    "X-Accel-Buffering": "no",
                    "Connection": "keep-alive",
                }
            )
        else:
            # It's a direct URL - proxy it to avoid CDN 403s and preserve headers
            try:
                upstream = file_or_url
                if fast and not proxy:
                    # Prefer a direct 3xx redirect to the CDN for maximum speed
                    return RedirectResponse(url=upstream, status_code=302)
                range_header = request.headers.get("Range") if isinstance(request, Request) else None

                content_length = None
                content_type = None

                def stream_upstream() -> Iterator[bytes]:
                    headers = {
                        "User-Agent": os.environ.get("USER_AGENT", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
                        "Accept": "*/*",
                        "Accept-Language": os.environ.get("ACCEPT_LANGUAGE", "en-US,en;q=0.9"),
                        "Referer": url,
                        "Connection": "keep-alive",
                    }
                    if range_header:
                        headers["Range"] = range_header
                    cookies_jar = None
                    try:
                        from requests.cookies import RequestsCookieJar  # type: ignore
                        # Optionally, load from auth_manager cookiefile into requests jar
                        from backend.auth_manager import auth_manager
                        cookiefile = auth_manager.get_cookies_file(platform)
                        if cookiefile and os.path.exists(cookiefile):
                            try:
                                # Minimal netscape -> jar import
                                jar = RequestsCookieJar()
                                with open(cookiefile, 'r', encoding='utf-8', errors='ignore') as cf:
                                    for line in cf:
                                        if not line or line.startswith('#') or '\t' not in line:
                                            continue
                                        parts = line.strip().split('\t')
                                        if len(parts) >= 7:
                                            domain, _, path, secure, expires, name, value = parts[:7]
                                            jar.set(name, value, domain=domain, path=path)
                                cookies_jar = jar
                            except Exception:
                                cookies_jar = None
                    except Exception:
                        cookies_jar = None

                    # Probe upstream headers once to capture Content-Length/Type for the response
                    nonlocal content_length, content_type
                    try:
                        head = requests.head(upstream, headers=headers, cookies=cookies_jar, allow_redirects=True, timeout=15)
                        if head.ok:
                            content_length = head.headers.get("Content-Length")
                            content_type = head.headers.get("Content-Type")
                    except Exception:
                        pass

                    with requests.get(upstream, headers=headers, cookies=cookies_jar, stream=True, timeout=30) as r:
                        r.raise_for_status()
                        # Larger chunk size reduces Python overhead and can significantly improve throughput
                        iter_chunk_size = max(8192, int(os.environ.get("STREAM_CHUNK_SIZE", 1024 * 256)))
                        for chunk in r.iter_content(chunk_size=iter_chunk_size):
                            if chunk:
                                yield chunk

                resp_headers = {
                    "Content-Disposition": f'attachment; filename="{filename}"',
                    "Cache-Control": "no-cache",
                    "Accept-Ranges": "bytes",
                    "X-Accel-Buffering": "no",
                    "Connection": "keep-alive",
                }

                # Prefer upstream content-type, else infer from filename extension when proxying
                ext = os.path.splitext(filename or "")[1].lstrip(".") if filename else "mp4"
                media_type = content_type or get_content_type(ext)

                # Range-aware response headers
                status_code = 200
                if range_header:
                    status_code = 206
                    # Try to set Content-Range and proper Content-Length for partial responses
                    # First, try using HEAD response Content-Range if present
                    content_range_hdr = None
                    try:
                        # Reuse the values from the HEAD probe if available
                        # content_length here may be total length on 200 or partial length on 206, depends on upstream
                        pass
                    except Exception:
                        pass

                    try:
                        # Attempt to get Content-Range via a HEAD probe result if available
                        # We stored nothing explicitly; re-run a cheap parse from the Range header and total length
                        # Format: "bytes=start-end" (single-range assumed)
                        if content_length and isinstance(content_length, str) and content_length.isdigit():
                            total_len = int(content_length)
                        else:
                            total_len = None

                        # Parse client range header (single range only)
                        rng = range_header.strip().lower()
                        # Expecting: bytes=start-end or bytes=start-
                        if rng.startswith("bytes="):
                            part = rng.split("=", 1)[1].split(",", 1)[0].strip()
                            start_str, _, end_str = part.partition("-")
                            start = int(start_str) if start_str.isdigit() else None
                            end = int(end_str) if end_str.isdigit() else None

                            if start is not None and total_len:
                                if end is None or end >= total_len:
                                    end = total_len - 1
                                if end >= start and total_len > 0:
                                    resp_headers["Content-Range"] = f"bytes {start}-{end}/{total_len}"
                                    resp_headers["Content-Length"] = str((end - start) + 1)
                    except Exception:
                        # If anything fails, omit Content-Range/Length (browser will still handle 206)
                        pass
                else:
                    # Non-range, set Content-Length when known
                    if content_length and isinstance(content_length, str) and content_length.isdigit():
                        resp_headers["Content-Length"] = content_length

                return StreamingResponse(stream_upstream(), media_type=media_type, headers=resp_headers, status_code=status_code)
            except Exception:
                # Fallback to redirect if proxying fails (should be rare)
                return RedirectResponse(url=file_or_url, status_code=307)
            
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error downloading {platform} video {url}: {e}")
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")

# Convenience endpoints for each platform
@app.get("/youtube/info")
async def youtube_info_endpoint(url: str = Query(...)):
    """Get YouTube video information."""
    return await get_platform_info("youtube", url)

@app.get("/youtube/download")
@app.head("/youtube/download")
async def youtube_download_endpoint(
    url: str = Query(...),
    format_id: str = Query("best"),
    filename: Optional[str] = Query(None),
    background_tasks: BackgroundTasks = None
):
    """Download YouTube video."""
    return await download_from_platform("youtube", url, format_id, filename, background_tasks)

@app.get("/instagram/info")
async def instagram_info_endpoint(url: str = Query(...)):
    """Get Instagram video information."""
    return await get_platform_info("instagram", url)

@app.get("/instagram/download")
@app.head("/instagram/download")
async def instagram_download_endpoint(
    url: str = Query(...),
    format_id: str = Query("best"),
    filename: Optional[str] = Query(None),
    background_tasks: BackgroundTasks = None
):
    """Download Instagram video."""
    return await download_from_platform("instagram", url, format_id, filename, background_tasks)

@app.get("/instagram/debug")
async def instagram_debug_endpoint(url: str = Query(...)):
    """Debug Instagram thumbnail and media extraction."""
    try:
        import yt_dlp
        from backend.platforms.base import build_ydl_opts
        
        # Get raw yt-dlp data
        ydl_opts = build_ydl_opts({
            'skip_download': True,
            'http_headers': {
                'Referer': 'https://www.instagram.com/',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                'Accept-Language': 'en-US,en;q=0.9'
            }
        }, platform="instagram")
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            raw_info = ydl.extract_info(url, download=False)
        
        # Also get processed info
        from backend.platforms.instagram import analyze
        processed_info = analyze(url)
        
        return {
            "success": True,
            "url": url,
            "raw_data": {
                "title": raw_info.get('title'),
                "thumbnail": raw_info.get('thumbnail'),
                "display_resources": raw_info.get('display_resources'),
                "thumbnails": raw_info.get('thumbnails'),
                "display_url": raw_info.get('display_url'),
                "formats": len(raw_info.get('formats', [])),
                "entries": len(raw_info.get('entries', [])) if raw_info.get('_type') == 'playlist' else 1
            },
            "processed_data": {
                "title": processed_info.get('title'),
                "thumbnail": processed_info.get('thumbnail'),
                "media_type": processed_info.get('media_type'),
                "formats_count": len(processed_info.get('formats', [])),
                "mp4_count": len(processed_info.get('mp4', [])),
                "jpg_count": len(processed_info.get('jpg', [])),
                "images_count": len(processed_info.get('images', []))
            }
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "url": url
        }

@app.get("/facebook/info")
async def facebook_info_endpoint(url: str = Query(...)):
    """Get Facebook video information."""
    return await get_platform_info("facebook", url)

@app.get("/facebook/download")
@app.head("/facebook/download")
async def facebook_download_endpoint(
    url: str = Query(...),
    format_id: str = Query("best"),
    filename: Optional[str] = Query(None),
    background_tasks: BackgroundTasks = None
):
    """Download Facebook video is disabled. Use instant download instead."""
    raise HTTPException(status_code=403, detail="Server download is disabled for Facebook. Use instant download.")

@app.get("/tiktok/info")
async def tiktok_info_endpoint(url: str = Query(...)):
    """Get TikTok video information."""
    return await get_platform_info("tiktok", url)

@app.get("/tiktok/download")
@app.head("/tiktok/download")
async def tiktok_download_endpoint(
    url: str = Query(...),
    format_id: str = Query("best"),
    filename: Optional[str] = Query(None),
    background_tasks: BackgroundTasks = None
):
    """Download TikTok video."""
    return await download_from_platform("tiktok", url, format_id, filename, background_tasks)

@app.get("/twitter/info")
async def twitter_info_endpoint(url: str = Query(...)):
    """Get Twitter video information."""
    return await get_platform_info("twitter", url)

@app.get("/twitter/download")
@app.head("/twitter/download")
async def twitter_download_endpoint(
    url: str = Query(...),
    format_id: str = Query("best"),
    filename: Optional[str] = Query(None),
    background_tasks: BackgroundTasks = None
):
    """Download Twitter video."""
    return await download_from_platform("twitter", url, format_id, filename, background_tasks)

@app.get("/pinterest/info")
async def pinterest_info_endpoint(url: str = Query(...)):
    """Get Pinterest video information."""
    return await get_platform_info("pinterest", url)

@app.get("/pinterest/download")
@app.head("/pinterest/download")
async def pinterest_download_endpoint(
    url: str = Query(...),
    format_id: str = Query("best"),
    filename: Optional[str] = Query(None),
    background_tasks: BackgroundTasks = None
):
    """Download Pinterest video."""
    return await download_from_platform("pinterest", url, format_id, filename, background_tasks, request)

# Unified stream endpoint (auto-detect platform)
@app.get("/api/stream")
@app.head("/api/stream")
async def unified_stream(
    url: str = Query(...),
    format_id: str = Query("best"),
    filename: Optional[str] = Query(None),
    background_tasks: BackgroundTasks = None
):
    try:
        platform = detect_platform(url)
        if not platform or platform not in PLATFORM_HANDLERS:
            raise HTTPException(status_code=400, detail="Unsupported or invalid URL for streaming")
        return await download_from_platform(platform, url, format_id, filename, background_tasks)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unified stream failed for {url}: {e}")
        raise HTTPException(status_code=500, detail="Stream failed")

# Generic passthrough/proxy endpoint for direct media URLs (e.g., images)
@app.get("/api/passthrough")
@app.head("/api/passthrough")
async def passthrough(
    url: str = Query(..., description="Direct media URL to proxy"),
    filename: Optional[str] = Query(None, description="Suggested filename for download"),
    request: Request = None
):
    try:
        # Infer content type from URL extension as a hint
        ext = ""
        try:
            from urllib.parse import urlparse
            path = urlparse(url).path
            if "." in path:
                ext = path.split(".")[-1].lower()
        except Exception:
            pass
        content_type = get_content_type(ext or "bin")

        range_header = request.headers.get("Range") if isinstance(request, Request) else None

        def stream_upstream() -> Iterator[bytes]:
            headers = {
                "User-Agent": os.environ.get("USER_AGENT", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
                "Accept": "*/*",
                "Accept-Language": os.environ.get("ACCEPT_LANGUAGE", "en-US,en;q=0.9"),
                "Referer": url,
                "Connection": "keep-alive",
            }
            if range_header:
                headers["Range"] = range_header
            try:
                from backend.utils_cookies import load_requests_cookiejar
                cookies_jar = load_requests_cookiejar()
            except Exception:
                cookies_jar = None
            with requests.get(url, headers=headers, cookies=cookies_jar, stream=True, timeout=30) as r:
                r.raise_for_status()
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        yield chunk

        resp_headers = {
            "Content-Disposition": f'attachment; filename="{filename or "download"}"',
            "Cache-Control": "no-cache",
            "Accept-Ranges": "bytes",
        }
        status_code = 206 if (request and request.headers.get("Range")) else 200
        return StreamingResponse(stream_upstream(), media_type=content_type, headers=resp_headers, status_code=status_code)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Passthrough failed for {url}: {e}")
        raise HTTPException(status_code=500, detail="Passthrough failed")

# Cookies upload endpoint (similar to Flask route)
from fastapi import UploadFile, File, Form

COOKIES_DEFAULT_PATH = os.environ.get("COOKIES_FILE", str(Path("e:/project/downloader/cookies.txt")))

def _persist_env_var(key: str, value: str, dotenv_path: str = "e:/project/downloader/.env") -> None:
    """Create/update a .env file with key=value. Keep existing entries and comments."""
    try:
        lines = []
        if os.path.exists(dotenv_path):
            with open(dotenv_path, 'r', encoding='utf-8') as f:
                lines = f.read().splitlines()
        found = False
        new_lines = []
        for line in lines:
            if not line.strip() or line.strip().startswith('#'):
                new_lines.append(line)
                continue
            k = line.split('=', 1)[0].strip()
            if k == key:
                new_lines.append(f"{key}={value}")
                found = True
            else:
                new_lines.append(line)
        if not found:
            new_lines.append(f"{key}={value}")
        with open(dotenv_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(new_lines) + '\n')
        logger.info(f"Persisted {key} to {dotenv_path}")
    except Exception as e:
        logger.warning(f"Failed to persist {key} to .env: {e}")

@app.post("/cookies/upload")
async def upload_cookies(file: UploadFile = File(...), persist_path: str = Form(None)):
    """Upload a cookies.txt file (Netscape format) used by downloaders.
    - Saves to COOKIES_FILE env path if set, otherwise to repo root cookies.txt.
    - Optionally persist a custom path by passing persist_path form field.
    """
    try:
        # Determine destination path
        dest_path = persist_path or COOKIES_DEFAULT_PATH
        dest = Path(dest_path)
        dest.parent.mkdir(parents=True, exist_ok=True)

        # Basic validation: size limit (~2MB) and text-like content
        contents = await file.read()
        if len(contents) > 2 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Cookies file too large (max 2MB)")
        text = contents.decode('utf-8', errors='ignore')
        # Heuristic check for Netscape cookie file format markers
        if ("# Netscape HTTP Cookie File" not in text) and (".youtube." not in text and "SID" not in text and "HSID" not in text):
            logger.warning("Uploaded cookies.txt does not look like Netscape format; proceeding anyway")

        # Backup existing
        if dest.exists():
            backup = dest.with_suffix(dest.suffix + ".bak")
            try:
                dest.replace(backup)
            except Exception:
                pass

        # Write
        with open(dest, 'wb') as f:
            f.write(contents)

        # Persist env var if custom path requested or env not set
        if persist_path or not os.environ.get("COOKIES_FILE"):
            _persist_env_var("COOKIES_FILE", str(dest))
            os.environ["COOKIES_FILE"] = str(dest)

        return {"ok": True, "path": str(dest), "size": len(contents)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to upload cookies: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload cookies")

# Serve the web interface
@app.get("/", response_class=HTMLResponse)
def serve_frontend():
    """Serve the web interface."""
    try:
        with open("frontend/downloader.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="""
        <html>
            <body>
                <h1>Multi-Platform Video Downloader API v2.0</h1>
                <p>Frontend not found. API endpoints available:</p>
                <ul>
                    <li><a href="/docs">API Documentation</a></li>
                    <li><a href="/platforms">Supported Platforms</a></li>
                    <li><a href="/health">Health Check</a></li>
                </ul>
            </body>
        </html>
        """)

# Signing for instant downloads (v2)
SECRET = os.getenv("SIGN_SECRET", "change-me")
TOKEN_TTL = int(os.getenv("SIGN_TTL_SECONDS", "900"))  # 15 minutes


def _sign_payload(payload: Dict[str, Any]) -> str:
    msg = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    sig = hmac.new(SECRET.encode("utf-8"), msg, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(msg + b"." + sig).decode("ascii")


def _verify_token(token: str) -> Dict[str, Any]:
    raw = base64.urlsafe_b64decode(token.encode("ascii"))
    msg, sig = raw.rsplit(b".", 1)
    expected = hmac.new(SECRET.encode("utf-8"), msg, hashlib.sha256).digest()
    if not hmac.compare_digest(sig, expected):
        raise HTTPException(status_code=400, detail="Bad token signature")
    payload = json.loads(msg.decode("utf-8"))
    if int(payload.get("exp", 0)) < int(time.time()):
        raise HTTPException(status_code=410, detail="Token expired")
    return payload


@app.get("/api/v2/sign")
async def api_v2_sign(url: str = Query(...), format_id: str = Query("best"), filename: Optional[str] = None):
    # Create a short-lived token that the /dl endpoint will resolve
    exp = int(time.time()) + TOKEN_TTL
    payload = {"url": url, "format_id": format_id, "filename": filename, "exp": exp}
    token = _sign_payload(payload)
    return {"token": token, "dl": f"/dl?token={quote(token)}"}


@app.get("/dl")
@app.head("/dl")
async def api_v2_dl(token: str = Query(...)):
    # Verify token then resolve and proxy via unified_stream to avoid 403s
    payload = _verify_token(token)
    url = payload.get("url")
    format_id = payload.get("format_id") or "best"
    filename = payload.get("filename")
    # Reuse unified stream which auto-detects platform
    return await unified_stream(url=url, format_id=format_id, filename=filename)


# API info endpoint
@app.get("/api")
def api_info():
    """API documentation."""
    return {
        "message": "Multi-Platform Video Downloader API",
        "version": "2.0.0",
        "platforms": list(PLATFORM_HANDLERS.keys()),
        "endpoints": {
            "info": "/{platform}/info?url=VIDEO_URL",
            "download": "/{platform}/download?url=VIDEO_URL&format_id=FORMAT_ID",
            "detect": "/detect?url=VIDEO_URL",
            "health": "/health",
            "v2_sign": "/api/v2/sign?url=...&format_id=...&filename=...",
            "v2_dl": "/dl?token=...",
            "v2_info": "/api/v2/{platform}/info?url=...",
            "v2_download": "/api/v2/{platform}/download",
            "v2_task": "/api/v2/task/{task_id}"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8003, reload=True)