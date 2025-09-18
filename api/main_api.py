import os
import json
import asyncio
import time
import uuid
import importlib
import re
from typing import Dict, Any, Optional, List
from urllib.parse import urljoin

import yt_dlp
from fastapi import FastAPI, HTTPException, Query, Response, BackgroundTasks, Body, Request, Depends, Header
from fastapi.responses import JSONResponse, RedirectResponse, FileResponse, StreamingResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from celery.result import AsyncResult
from backend.tasks.celery_app import celery
from backend.tasks.download import download_task
from backend.tasks.universal_download import universal_download_task
from backend.tasks.progress import get_progress
from backend.platforms.base import build_ydl_opts
from backend.utils.sign import make_token, verify_token
from backend.auth_manager import auth_manager

# Optional Redis cache
try:
    import redis  # type: ignore
except Exception:
    redis = None  # fallback to in-memory

# Optional async HTTP client for passthrough/HEAD validation
try:
    import httpx  # type: ignore
except Exception:
    httpx = None

# Load environment variables from .env (for COOKIES_FILE, FFMPEG_LOCATION, etc.)
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv(dotenv_path="e:\\project\\downloader\\.env")
except Exception:
    pass

APP = FastAPI(title="Universal Downloader API", version="2.0")
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-key-change-in-production")

# Concurrency control: limit simultaneous yt-dlp extractions to prevent resource exhaustion
_extraction_semaphore = asyncio.Semaphore(5)  # Allow up to 5 concurrent extractions

# API key configuration (comma-separated keys supported)
_API_KEYS: List[str] = []
try:
    _API_KEYS = [k.strip() for k in os.getenv("API_KEYS", os.getenv("API_KEY", "")).split(",") if k.strip()]
except Exception:
    _API_KEYS = []

async def require_api_key(x_api_key: Optional[str] = Header(None)) -> None:
    """Require X-API-Key header when API keys are configured.
    If no API keys are configured, the check is skipped (useful for local/dev).
    """
    if not _API_KEYS:
        return  # No keys configured -> allow
    if not x_api_key or x_api_key not in _API_KEYS:
        # 401 to signal auth required; frontend/clients should pass X-API-Key
        raise HTTPException(status_code=401, detail="Unauthorized: invalid or missing API key")

# Fix 404s for common asset requests by providing redirects/aliases
@APP.get("/static/og-default.png")
async def _alias_og_default_png():
    return RedirectResponse(url="/static/og-default.svg", status_code=307)

@APP.get("/favicon.ico")
async def _favicon_alias():
    # Redirect to existing SVG placeholder; avoids 404 noise
    return RedirectResponse(url="/static/og-default.svg", status_code=307)

from fastapi.staticfiles import StaticFiles  # type: ignore

# Templates and static files
templates = Jinja2Templates(directory=os.path.join(os.getcwd(), "templates"))
APP.mount("/static", StaticFiles(directory=os.path.join(os.getcwd(), "static")), name="static")

# Health check
@APP.get("/health")
async def _health():
    return {"status": "ok"}

# Minimal UI routes
@APP.get("/", response_class=HTMLResponse)
async def _root(request: Request):
    # Render a simple chooser landing instead of redirecting
    return templates.TemplateResponse("index.html", {"request": request})

@APP.get("/universal_tailwind", response_class=HTMLResponse)
async def _universal_tailwind(request: Request):
    return templates.TemplateResponse("universal_tailwind.html", {"request": request})

# @APP.get("/instant_only", response_class=HTMLResponse)
# async def _instant_only(request: Request):
#     # Instant-only page disabled
#     return RedirectResponse(url="/universal_tailwind", status_code=307)

# CORS (allow your frontend to call API)
try:
    from fastapi.middleware.cors import CORSMiddleware  # type: ignore
    APP.add_middleware(
        CORSMiddleware,
        allow_origins=os.getenv("CORS_ALLOW_ORIGINS", "*").split(","),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
except Exception:
    pass

DOWNLOADS_DIR = os.path.abspath(os.getenv("DOWNLOAD_FOLDER", os.path.join(os.getcwd(), "downloads")))
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

# Cache setup: Redis preferred, fallback to in-memory dicts
REDIS_URL = os.getenv("REDIS_URL")
_redis = None
if REDIS_URL and redis:
    try:
        _redis = redis.from_url(REDIS_URL, decode_responses=True)
    except Exception:
        _redis = None

# Simple in-memory cache fallback
_info_cache: Dict[str, Dict[str, Any]] = {}
_url_cache: Dict[str, Dict[str, Any]] = {}
try:
    _CACHE_TTL = int(os.getenv("CACHE_TTL_SECONDS", "0"))
    if _CACHE_TTL <= 0:
        _CACHE_TTL = int(os.getenv("CACHE_TTL_MINUTES", "30")) * 60
except Exception:
    _CACHE_TTL = 60 * 30  # default 30 minutes


def _cache_set(key: str, value: Dict[str, Any], ttl: int = _CACHE_TTL) -> None:
    """Set cache value. Prefer Redis, but fall back to in-memory on any error."""
    payload = json.dumps({"value": value, "ts": int(time.time())})
    if _redis is not None:
        try:
            _redis.setex(key, ttl, payload)
            return
        except Exception:
            # Fall back to in-memory cache if Redis is unreachable or errors
            pass
    _info_cache[key] = {"value": value, "expire": time.time() + ttl}


def _cache_get(key: str) -> Optional[Dict[str, Any]]:
    """Get cache value. Prefer Redis, but fall back to in-memory on any error."""
    if _redis is not None:
        try:
            raw = _redis.get(key)
        except Exception:
            raw = None
        if raw:
            try:
                return json.loads(raw)
            except Exception:
                return None
    data = _info_cache.get(key)
    if not data:
        return None
    if data.get("expire", 0) < time.time():
        _info_cache.pop(key, None)
        return None
    return {"value": data["value"], "ts": int(time.time())}


class InfoResponse(BaseModel):
    id: str
    title: str
    thumbnail: Optional[str]
    duration: Optional[int]
    author: Optional[str]
    media_type: str  # "video" or "image"
    formats: List[Dict[str, Any]]


def _dedupe_best_per_height_mp4(formats: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    best: Dict[int, Dict[str, Any]] = {}
    for f in formats or []:
        ext = (f.get("ext") or "").lower()
        h = f.get("height") or 0
        if ext != "mp4" or h <= 0:
            continue
        # Prefer AVC/H.264 for compatibility
        vcodec = (f.get("vcodec") or "").lower()
        if not (vcodec.startswith("avc") or "h264" in vcodec or vcodec in ("none", "h264")):
            continue
        cur = best.get(h)
        if not cur:
            best[h] = f
            continue
        # Prefer higher tbr/fps when same height
        cur_tbr = cur.get("tbr") or 0
        new_tbr = f.get("tbr") or 0
        if new_tbr > cur_tbr or (f.get("fps") or 0) > (cur.get("fps") or 0):
            best[h] = f
    return [best[h] for h in sorted(best.keys(), reverse=True)]


def _build_formats(info: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Build a list of user-facing formats including progressive MP4 and audio-only.
    - Progressive MP4 entries are suitable for instant/direct streaming.
    - Audio-only entries (e.g., m4a/webm) are also streamable instantly.
    - MP3 entries remain server-side conversions (marked accordingly).
    """
    fmts = info.get("formats") or []

    # Progressive MP4 (video+audio), dedup by height
    selected = _dedupe_best_per_height_mp4(fmts)

    out: List[Dict[str, Any]] = []

    # Add progressive MP4 options
    for f in selected:
        filesize = f.get("filesize") or f.get("filesize_approx")
        size_mb = round(filesize / (1024 * 1024), 1) if filesize else None
        out.append({
            "format_id": f.get("format_id"),
            "ext": "mp4",
            "quality": f.get("format_note") or (f"{f.get('height')}p" if f.get("height") else "Unknown"),
            "resolution": f.get("resolution") or (f"{f.get('width','?')}x{f.get('height','?')}") ,
            "filesize_mb": size_mb,
            "vcodec": f.get("vcodec"),
            "acodec": f.get("acodec"),
            "fps": f.get("fps"),
            "tbr": f.get("tbr"),
            "height": f.get("height"),
        })

    # Best audio-only (instant, no conversion) — expose a couple of top options
    audio_only = [
        f for f in fmts
        if (f.get("acodec") and f.get("acodec") != "none") and (not f.get("vcodec") or f.get("vcodec") == "none")
    ]

    def _abr_kbps(f: Dict[str, Any]) -> int:
        try:
            return int(f.get("abr") or f.get("tbr") or 0)
        except Exception:
            return 0

    audio_only.sort(key=lambda f: (_abr_kbps(f), f.get("filesize") or f.get("filesize_approx") or 0), reverse=True)

    for f in audio_only[:2]:  # top 1–2
        filesize = f.get("filesize") or f.get("filesize_approx")
        size_mb = round(filesize / (1024 * 1024), 1) if filesize else None
        br = _abr_kbps(f)
        ext = (f.get("ext") or "m4a").lower()
        out.append({
            "format_id": f.get("format_id"),
            "ext": ext,  # e.g., m4a/webm
            "quality": f"Best audio ({br} kbps)" if br else "Best audio",
            "resolution": None,
            "filesize_mb": size_mb,
            "vcodec": None,
            "acodec": f.get("acodec"),
            "fps": None,
            "tbr": br,
            "height": None,
        })

    # Keep MP3 options as server-side conversions
    for br in (128, 192, 320):
        out.append({
            "format_id": f"mp3_{br}",
            "ext": "mp3",
            "quality": f"MP3 {br}k (server)",
            "resolution": None,
            "filesize_mb": None,
            "vcodec": None,
            "acodec": "mp3",
            "fps": None,
            "tbr": br,
            "height": None,
        })

    return out


def _cache_keys_for(info: Dict[str, Any]) -> Dict[str, str]:
    vid = info.get("id") or "unknown"
    return {
        "info": f"info:{vid}",
        "urls": f"urls:{vid}",
    }


def _infer_platform(u: str) -> str:
    try:
        from urllib.parse import urlparse as _urlparse
        host = (_urlparse(u).hostname or '').lower()
    except Exception:
        host = ''
    if 'youtube.' in host or host in ('youtu.be', 'm.youtube.com'):
        return 'youtube'
    for name in ('instagram', 'facebook', 'tiktok', 'twitter', 'x.', 'pinterest', 'linkedin', 'reddit', 'snapchat', 'naver'):
        if name in host:
            # normalize x. -> twitter
            if name == 'x.':
                return 'twitter'
            return name
    return 'generic'


def _cookies_available(platform: str) -> bool:
    try:
        from backend.auth_manager import auth_manager as _am
        path = _am.get_cookies_file(platform)
    except Exception:
        path = None
    if not path:
        path = os.environ.get('COOKIES_FILE')
    if not path or not os.path.exists(path):
        return False
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            head = f.read(2048)
        return ('# Netscape HTTP Cookie File' in head) or ('\t' in head and not head.strip().startswith('{'))
    except Exception:
        return False


def _build_platform_headers(url: str, platform: str) -> Dict[str, str]:
    try:
        from urllib.parse import urlparse as _urlparse
        host = (_urlparse(url).netloc or 'example.com')
        base = f"https://{host}"
    except Exception:
        base = None
    headers = {
        'User-Agent': os.environ.get('USER_AGENT', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'),
        'Accept-Language': os.environ.get('ACCEPT_LANGUAGE', 'en-US,en;q=0.9'),
        'Accept': '*/*',
    }
    if platform != 'youtube' and base:
        headers['Referer'] = base + '/'
        headers['Origin'] = base
    if platform == 'youtube':
        headers['Origin'] = 'https://www.youtube.com'
        headers['Referer'] = 'https://www.youtube.com/'
    elif platform == 'instagram':
        # Hardened headers for Instagram
        headers['Sec-Fetch-Mode'] = 'navigate'
        headers['Sec-Fetch-Site'] = 'same-origin'
        headers['Sec-Fetch-User'] = '?1'
        headers['Upgrade-Insecure-Requests'] = '1'
        headers['Accept'] = 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
    elif platform == 'tiktok':
        # Hardened headers for TikTok
        headers['Referer'] = 'https://www.tiktok.com/'
        headers['Origin'] = 'https://www.tiktok.com'
        headers['Accept'] = 'text/html,application/json;q=0.9,*/*;q=0.8'
        headers['Sec-Fetch-Mode'] = 'navigate'
        headers['Sec-Fetch-Site'] = 'same-origin'
        headers['Upgrade-Insecure-Requests'] = '1'
    elif platform == 'linkedin':
        # Hardened headers for LinkedIn
        headers['Referer'] = 'https://www.linkedin.com/'
        headers['Origin'] = 'https://www.linkedin.com'
        headers['Accept'] = 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        headers['Sec-Fetch-Mode'] = 'navigate'
        headers['Sec-Fetch-Site'] = 'same-origin'
        headers['Upgrade-Insecure-Requests'] = '1'
    elif platform == 'reddit':
        # Hardened headers for Reddit and v.redd.it
        headers['Referer'] = 'https://www.reddit.com/'
        headers['Origin'] = 'https://www.reddit.com'
        headers['Accept'] = 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        headers['Sec-Fetch-Mode'] = 'navigate'
        headers['Sec-Fetch-Site'] = 'same-origin'
        headers['Upgrade-Insecure-Requests'] = '1'
    return headers


async def _extract_info_timeout(url: str, ydl_opts: Dict[str, Any], timeout_sec: int = 25):
    def _do_extract():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(url, download=False)
    try:
        async with _extraction_semaphore:
            return await asyncio.wait_for(asyncio.to_thread(_do_extract), timeout=timeout_sec)
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail='Extractor timeout')


async def _head_ok(url: str) -> bool:
    if not httpx:
        return True
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            r = await client.head(url)
            return r.status_code == 200
    except Exception:
        return False


def _resolve_direct_url(info: Dict[str, Any], format_id: str) -> Optional[str]:
    # Try to find exact format id first
    for f in (info.get("formats") or []):
        if str(f.get("format_id")) == str(format_id):
            return f.get("url")
    # Smarter "best": prefer progressive MP4 for fastest start
    if format_id == "best":
        fid = _pick_fast_best_format_id(info)
        if fid:
            for f in (info.get("formats") or []):
                if str(f.get("format_id")) == str(fid):
                    return f.get("url")
        # Fallback to extractor-provided best URL
        return info.get("url") or None
    return None


# --- Fast path helpers: progressive detection, smart best, and speculative prefetch ---

# Canonicalize YouTube URLs to https://www.youtube.com/watch?v=ID[&t=Ss]
# Improves cache hits and consistency across endpoints.
from urllib.parse import urlparse as _urlparse, parse_qs as _parse_qs

def _parse_time_to_seconds_py(t: Optional[str]) -> Optional[int]:
    if not t:
        return None
    try:
        if t.isdigit():
            return int(t)
    except Exception:
        pass
    try:
        import re as _re
        if _re.match(r"^\d{1,2}:\d{1,2}(:\d{1,2})?$", t):
            parts = [int(x) for x in t.split(":")]
            if len(parts) == 2:
                return parts[0] * 60 + parts[1]
            if len(parts) == 3:
                return parts[0] * 3600 + parts[1] * 60 + parts[2]
        m = _re.match(r"(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?", t)
        if m:
            h = int(m.group(1) or 0)
            mn = int(m.group(2) or 0)
            s = int(m.group(3) or 0)
            return h * 3600 + mn * 60 + s
    except Exception:
        return None
    return None


def _canonicalize_youtube_url(raw: str) -> Optional[str]:
    if not raw:
        return None
    try:
        import re as _re
        s = raw.strip()
        if _re.match(r"^[A-Za-z0-9_-]{11}$", s):
            return f"https://www.youtube.com/watch?v={s}"
        if not (s.startswith("http://") or s.startswith("https://")):
            s = "https://" + s
        u = _urlparse(s)
        host = (u.hostname or "").lower()
        path = u.path or ""
        qs = _parse_qs(u.query or "")
        if _re.search(r"youtu\.be/([A-Za-z0-9_-]{11})", s):
            vid = _re.search(r"youtu\.be/([A-Za-z0-9_-]{11})", s).group(1)
            t = qs.get("t") or qs.get("start") or qs.get("time_continue")
            secs = _parse_time_to_seconds_py(t[0]) if t else None
            base = f"https://www.youtube.com/watch?v={vid}"
            return base + (f"&t={secs}s" if secs else "")
        if ("youtube." in host) or (host in ("m.youtube.com", "music.youtube.com", "www.youtube-nocookie.com")):
            if path.startswith("/watch"):
                vid = (qs.get("v") or [None])[0]
                t = (qs.get("t") or qs.get("start") or qs.get("time_continue") or [None])[0]
                secs = _parse_time_to_seconds_py(t) if t else None
                if vid:
                    base = f"https://www.youtube.com/watch?v={vid}"
                    return base + (f"&t={secs}s" if secs else "")
            em = _re.search(r"/embed/([A-Za-z0-9_-]{11})", path)
            if em:
                return f"https://www.youtube.com/watch?v={em.group(1)}"
            sh = _re.search(r"/shorts/([A-Za-z0-9_-]{11})", path)
            if sh:
                return f"https://www.youtube.com/watch?v={sh.group(1)}"
            vm = _re.search(r"/v/([A-Za-z0-9_-]{11})", path)
            if vm:
                return f"https://www.youtube.com/watch?v={vm.group(1)}"
        m2 = _re.search(r"([A-Za-z0-9_-]{11})", s)
        if m2:
            return f"https://www.youtube.com/watch?v={m2.group(1)}"
    except Exception:
        return None
    return None


def _normalize_input_url(url: str) -> str:
    try:
        u = url.strip()
        p = _urlparse(u if u.startswith("http") else ("https://" + u))
        host = (p.hostname or '').lower()
        if ('youtube.' in host) or (host in ('youtu.be', 'm.youtube.com', 'music.youtube.com', 'www.youtube-nocookie.com')):
            canon = _canonicalize_youtube_url(url)
            return canon or url
        return url
    except Exception:
        return url


def _is_progressive_mp4(f: Dict[str, Any]) -> bool:
    if not f:
        return False
    if (f.get("acodec") == "none") or (f.get("vcodec") == "none"):
        return False
    if (f.get("ext") or "").lower() != "mp4":
        return False
    proto = (f.get("protocol") or "").lower()
    if "m3u8" in proto or "hls" in proto:
        return False
    return True


def _pick_fast_best_format_id(item: Dict[str, Any]) -> Optional[str]:
    formats = item.get("formats") or []
    progressive = [f for f in formats if _is_progressive_mp4(f)]
    if not progressive:
        return None
    # Prefer 720p, then 480p, then 360p
    def _h(f):
        try:
            return int(f.get("height") or 0)
        except Exception:
            return 0
    progressive.sort(key=lambda f: (_h(f), f.get("tbr") or 0), reverse=True)
    targets = [720, 480, 360]
    for t in targets:
        for f in progressive:
            if _h(f) == t:
                return str(f.get("format_id"))
    # Fallback to highest progressive
    return str(progressive[0].get("format_id")) if progressive else None


async def _prefetch_direct_urls(item: Dict[str, Any]) -> None:
    try:
        vid = item.get("id")
        if not vid:
            return
        keys = _cache_keys_for(item)
        mapping = (_cache_get(keys["urls"]) or {}).get("value") or {}
        # collect candidates: progressive mp4s
        for f in (item.get("formats") or []):
            fid = str(f.get("format_id"))
            direct = f.get("url")
            if not fid or not direct:
                continue
            if not _is_progressive_mp4(f):
                continue
            if fid in mapping:
                continue
            if (not httpx) or (await _head_ok(direct)):
                mapping[fid] = direct
        # also cache best if present
        if item.get("url") and ("best" not in mapping):
            direct_best = item.get("url")
            if (not httpx) or (await _head_ok(direct_best)):
                mapping["best"] = direct_best
        if mapping:
            _cache_set(keys["urls"], mapping)
    except Exception:
        # speculative optimization: ignore failures
        pass


@APP.get("/api/info")
async def api_info(
    url: str = Query(..., description="Media URL"),
    instant: int = Query(0, description="1=include progressive-only instant formats with direct URLs"),
    multi: int = Query(0, description="1=return multi-item arrays when available (e.g., Instagram carousels)")
):
    # Canonicalize YouTube to boost cache hits and consistency
    url = _normalize_input_url(url)
    url_key = f"map:{url}"

    # Fast path for PDFs (treat as direct file without yt-dlp)
    try:
        from urllib.parse import urlparse as _urlparse
        _p = _urlparse(url)
        _path = (_p.path or '').lower()
        if _path.endswith('.pdf'):
            title = (_path.rsplit('/', 1)[-1]) or 'document.pdf'
            resp = {
                "id": title,
                "title": title,
                "thumbnail": None,
                "duration": None,
                "author": _p.netloc,
                "media_type": "document",
                "formats": [],
                "progressive_formats": [
                    {"format_id": "direct", "ext": "pdf", "quality": "document", "filesize": None, "direct_url": url}
                ],
                "url": url
            }
            return resp
    except Exception:
        pass

    # If not instant: return cached normalized response immediately (backward compatible)
    if not instant:
        cached = _cache_get(url_key)
        if cached and cached.get("value"):
            return cached["value"]

    # Try to reuse cached raw info when instant=1
    item: Optional[Dict[str, Any]] = None
    if instant:
        cached_map = _cache_get(url_key)
        vid = (cached_map.get("value") or {}).get("id") if cached_map and cached_map.get("value") else None
        if vid:
            raw = _cache_get(f"info:{vid}")
            if raw and raw.get("value"):
                item = raw["value"]

    # Extract metadata when not available from cache
    if item is None:
        platform = _infer_platform(url)
        restricted = {"instagram", "facebook", "tiktok", "twitter", "pinterest", "linkedin", "reddit", "snapchat"}
        # Do not hard-require cookies; attempt extraction first to support public content.

        base_headers = _build_platform_headers(url, platform)
        ydl_opts = build_ydl_opts({'skip_download': True, 'http_headers': base_headers}, platform=platform)

        # Prefer fast YouTube client and skip HLS when possible
        if platform == 'youtube':
            ydl_opts.setdefault("extractor_args", {}).setdefault("youtube", {})["player_client"] = "android"
            ydl_opts["extractor_args"]["youtube"]["skip"] = ["hls"]
            # If this looks like a playlist/channel/feed, use flat extraction upfront for speed
            try:
                _u = url.lower()
                looks_multi = ("list=" in _u) or ("/playlist" in _u) or ("/channel/" in _u) or ("/c/" in _u) or ("/user/" in _u) or ("/@" in _u)
                if looks_multi:
                    ydl_opts['extract_flat'] = 'discard_in_playlist'
            except Exception:
                pass

        # Choose timeout and retries/backoff by platform
        if platform == 'youtube':
            primary_timeout, fallback_timeout = 15, 20
            max_attempts = 2
        elif platform in restricted:
            # With cookies present we can be more patient; without cookies, fail fast
            has_cookies = _cookies_available(platform)
            if platform == 'tiktok':
                # TikTok is often slower; add patience especially with cookies
                if has_cookies:
                    primary_timeout, fallback_timeout = 30, 40
                    max_attempts = 3
                else:
                    primary_timeout, fallback_timeout = 20, 30
                    max_attempts = 2
            else:
                if has_cookies:
                    primary_timeout, fallback_timeout = 25, 35
                    max_attempts = 3
                else:
                    primary_timeout, fallback_timeout = 15, 20
                    max_attempts = 2
        else:
            primary_timeout, fallback_timeout = 20, 25
            max_attempts = 2

        info = None
        delay = 0.8
        for attempt in range(1, max_attempts + 1):
            try:
                info = await _extract_info_timeout(url, ydl_opts, timeout_sec=primary_timeout)
                break
            except Exception:
                # Fallback: flat extraction on later attempts or when playlist
                fallback_opts = dict(ydl_opts)
                fallback_opts['extract_flat'] = 'discard_in_playlist'
                try:
                    info = await _extract_info_timeout(url, fallback_opts, timeout_sec=fallback_timeout)
                    break
                except Exception as e2:
                    # If this is a restricted platform without cookies, fail fast with clear message
                    if (platform in restricted) and (not _cookies_available(platform)) and attempt == max_attempts:
                        raise HTTPException(status_code=403, detail=f"{platform.capitalize()} may require cookies for this content. Provide COOKIES_FILE in .env.") from e2
                    if attempt == max_attempts:
                        info = None
                        break
                    await asyncio.sleep(delay)
                    delay *= 1.8  # exponential backoff

        if not info:
            raise HTTPException(status_code=502, detail="Failed to fetch info")
        # Normalize playlist/single (support multi=1 to expose all items)
        if info.get("_type") == "playlist" and info.get("entries"):
            items = [e for e in (info.get("entries") or []) if e]
            # Pick first video-like entry as representative item to avoid channel/profile timeouts
            def _pick_rep(entries):
                for e in entries:
                    if e.get('formats') or e.get('url') or e.get('webpage_url'):
                        return e
                return entries[0] if entries else {}
            item = _pick_rep(items)
        else:
            items = [info]
            item = info

    media_type = "video"
    if not (item.get("formats") or []) and (item.get("ext") in ("jpg", "png", "webp")):
        media_type = "image"
    # Mark collections (helps profiles/boards/pages report success without strict media)
    try:
        from urllib.parse import urlparse as _urlparse
        host = (_urlparse(url).hostname or '').lower()
        if ('items' in locals()) and items and len(items) > 1:
            if 'instagram.' in host:
                media_type = 'carousel'
            elif (('youtube.' in host) or (host in ('youtu.be', 'm.youtube.com'))):
                media_type = 'playlist'
            else:
                media_type = 'collection'
    except Exception:
        pass

    # Normalize thumbnail robustly for all platforms (esp. Instagram)
    # 1) Prefer provided 'thumbnail'
    # 2) Else pick largest from 'thumbnails'
    # 3) Else try common alt fields (thumbnail_url, display_url, display_resources[-1].src)
    # 4) Else fallback to local placeholder
    thumb = item.get("thumbnail")
    if not thumb:
        thumbs = item.get("thumbnails") or []
        if thumbs:
            try:
                thumb = sorted(thumbs, key=lambda t: (t.get('width') or 0, t.get('height') or 0))[-1].get('url') or thumbs[-1].get('url')
            except Exception:
                thumb = (thumbs[0] or {}).get('url')
    if not thumb:
        # Additional Instagram-style fallbacks
        thumb = (
            item.get("thumbnail_url")
            or item.get("display_url")
            or (
                item.get("display_resources", [{}])[-1].get("src")
                if isinstance(item.get("display_resources"), list)
                else None
            )
        )
    if not thumb:
        thumb = "/static/og-default.svg"

    # If this is a profile/board/page without direct media, return minimal success payload
    if media_type in ("playlist", "carousel") and not (item.get("formats") or []):
        resp: Dict[str, Any] = {
            "id": item.get("id") or "unknown",
            "title": item.get("title") or item.get("id") or "Unknown",
            "thumbnail": thumb,
            "duration": None,
            "author": item.get("uploader") or item.get("channel"),
            "media_type": media_type,
            "formats": [],
            "progressive_formats": [],
        }
    else:
        resp: Dict[str, Any] = {
            "id": item.get("id") or "unknown",
            "title": item.get("title") or item.get("id") or "Unknown",
            "thumbnail": thumb,
            "duration": item.get("duration"),
            "author": item.get("uploader") or item.get("channel"),
            "media_type": media_type,
            "formats": _build_formats(item),
        }

    # Multi-item support (e.g., Instagram carousels/profiles). Only include when requested
    if multi:
        def _shape_entry(e: Dict[str, Any]) -> Dict[str, Any]:
            # Minimal per-item shape with per-item progressive_formats
            fmts = e.get("formats") or []
            def _h(f: Dict[str, Any]) -> int:
                try:
                    return int(f.get("height") or 0)
                except Exception:
                    return 0
            prog = [
                {
                    "format_id": f.get("format_id"),
                    "ext": (f.get("ext") or "mp4").lower(),
                    "quality": f"{_h(f)}p" if _h(f) else "N/A",
                    "filesize": f.get("filesize") or f.get("filesize_approx"),
                    "direct_url": f.get("url"),
                }
                for f in fmts if _is_progressive_mp4(f)
            ]
            # Instagram/TikTok fallback: include first MP4 URL if no progressive detected
            try:
                from urllib.parse import urlparse as _urlparse
                host = (_urlparse(url).hostname or '').lower()
                if ('instagram.' in host or 'tiktok.' in host) and not prog:
                    fallback = [f for f in fmts if (f.get('url') and (f.get('ext') or '').lower() == 'mp4')]
                    if fallback:
                        f0 = fallback[0]
                        prog.append({
                            "format_id": f0.get("format_id"),
                            "ext": (f0.get("ext") or "mp4").lower(),
                            "quality": f"{_h(f0)}p" if _h(f0) else "Video",
                            "filesize": f0.get("filesize") or f0.get("filesize_approx"),
                            "direct_url": f0.get("url"),
                        })
            except Exception:
                pass
            # For YouTube flat entries without formats, try to derive a watch URL from id
            try:
                if (('youtube.' in host) or (host in ('youtu.be', 'm.youtube.com'))) and not prog and not fmts:
                    vid = e.get('id') or ''
                    if vid:
                        prog.append({
                            "format_id": "watch",
                            "ext": "mp4",
                            "quality": "N/A",
                            "filesize": None,
                            "direct_url": f"https://www.youtube.com/watch?v={vid}",
                        })
            except Exception:
                pass
            prog.sort(key=lambda x: (int(x.get("quality", "0").replace("p", "") or 0), x.get("filesize") or 0), reverse=True)
            return {
                "id": e.get("id"),
                "title": e.get("title") or e.get("id"),
                "thumbnail": e.get("thumbnail") or thumb,
                "media_type": ("video" if prog or fmts else ("image" if (e.get("ext") in ("jpg","png","webp")) else "unknown")),
                "formats": len(fmts),
                "progressive": len(prog),
                "progressive_formats": prog,
                "url": (prog[0].get("direct_url") if prog and prog[0].get("direct_url") else (fmts[0].get("url") if (fmts and fmts[0].get("url")) else None))
            }
        try:
            resp["items"] = [_shape_entry(e) for e in (items if 'items' in locals() else [item])]
        except Exception:
            pass

    # When instant=1, include progressive MP4 with direct URLs (no merge)
    if instant:
        fmts = item.get("formats") or []
        def _h(f: Dict[str, Any]) -> int:
            try:
                return int(f.get("height") or 0)
            except Exception:
                return 0
        progressive = [
            {
                "format_id": f.get("format_id"),
                "ext": (f.get("ext") or "mp4").lower(),
                "quality": f"{_h(f)}p" if _h(f) else "N/A",
                "filesize": f.get("filesize") or f.get("filesize_approx"),
                "direct_url": f.get("url"),
            }
            for f in fmts if _is_progressive_mp4(f)
        ]
        # If Instagram and no progressive found, still expose first MP4 URL if present
        try:
            from urllib.parse import urlparse as _urlparse
            host = (_urlparse(url).hostname or '').lower()
            if ('instagram.' in host or 'tiktok.' in host) and not progressive:
                fallback = [f for f in fmts if (f.get('url') and (f.get('ext') or '').lower() == 'mp4')]
                if fallback:
                    f0 = fallback[0]
                    progressive.append({
                        "format_id": f0.get("format_id"),
                        "ext": (f0.get("ext") or "mp4").lower(),
                        "quality": f"{_h(f0)}p" if _h(f0) else "Video",
                        "filesize": f0.get("filesize") or f0.get("filesize_approx"),
                        "direct_url": f0.get("url"),
                    })
        except Exception:
            pass
        progressive.sort(key=lambda x: (int(x.get("quality", "0").replace("p", "") or 0), x.get("filesize") or 0), reverse=True)
        resp["progressive_formats"] = progressive

        # Eagerly cache raw info, URL->response map (to expose id), and direct URLs per format
        keys = _cache_keys_for(item)
        _cache_set(keys["info"], item)
        try:
            mapping = (_cache_get(keys["urls"]) or {}).get("value") or {}
        except Exception:
            mapping = {}
        for p in progressive:
            fid = str(p.get("format_id")) if p.get("format_id") is not None else None
            direct = p.get("direct_url")
            if fid and direct:
                mapping[fid] = direct
        # Set a convenient "best" alias to top progressive item if present
        if progressive and progressive[0].get("direct_url"):
            mapping["best"] = progressive[0]["direct_url"]
        if mapping:
            _cache_set(keys["urls"], mapping)
        # Also map URL -> response so /api/redirect can infer video id without re-extraction
        _cache_set(url_key, resp)
    else:
        # Non-instant: cache raw info and full normalized response
        keys = _cache_keys_for(item)
        _cache_set(keys["info"], item)  # raw info
        _cache_set(url_key, resp)        # normalized response by URL

    # Speculative: prefetch progressive direct URLs and store mapping
    try:
        import asyncio as _asyncio
        _asyncio.create_task(_prefetch_direct_urls(item))
    except Exception:
        pass

    return resp


@APP.get("/instant")
async def instant_download(url: str = Query(..., description="YouTube video URL")):
    """Return a direct highest-quality progressive MP4 URL (with audio) without server-side download.
    This mirrors SaveFrom/Y2Mate-style instant links for fast starts.
    """
    try:
        # Check cache first
        url_key = f"map:{url}"
        cached = _cache_get(url_key)
        if cached and cached.get("value"):
            return cached["value"]

        # Extract metadata without downloading; prefer fast YouTube client and skip HLS
        ydl_opts = build_ydl_opts({'skip_download': True})
        ydl_opts.setdefault("extractor_args", {}).setdefault("youtube", {})["player_client"] = "android"
        ydl_opts["extractor_args"]["youtube"]["skip"] = ["hls"]

        # Make extraction async
        async def _extract_async():
            def _extract():
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    return ydl.extract_info(url, download=False)
            async with _extraction_semaphore:
                return await asyncio.to_thread(_extract)

        info = await _extract_async()

        if not info:
            raise HTTPException(status_code=502, detail="Failed to fetch info")

        # Normalize single vs playlist (pick first entry for playlists)
        item = info["entries"][0] if (info.get("_type") == "playlist" and info.get("entries")) else info

        # Choose best progressive MP4 (audio+video)
        formats = item.get("formats") or []
        mp4_candidates = [f for f in formats if _is_progressive_mp4(f)]
        if not mp4_candidates:
            raise HTTPException(status_code=404, detail="No progressive MP4 with audio available.")

        def _h(f):
            try:
                return int(f.get("height") or 0)
            except Exception:
                return 0

        mp4_candidates.sort(key=lambda f: (_h(f), f.get("tbr") or 0), reverse=True)
        best = mp4_candidates[0]
        direct = best.get("url")
        if not direct:
            raise HTTPException(status_code=410, detail="Direct URL not available")

        # Optionally validate URL (if httpx present)
        if not await _head_ok(direct):
            # Retry once after refetch
            info2 = await _extract_async()
            item2 = info2["entries"][0] if (info2.get("_type") == "playlist" and info2.get("entries")) else info2
            formats2 = item2.get("formats") or []
            mp4_candidates2 = [f for f in formats2 if _is_progressive_mp4(f)]
            mp4_candidates2.sort(key=lambda f: (_h(f), f.get("tbr") or 0), reverse=True)
            direct = (mp4_candidates2[0] or {}).get("url") if mp4_candidates2 else None
            if not direct or not await _head_ok(direct):
                raise HTTPException(status_code=410, detail="Direct URL expired")

        filesize = best.get("filesize") or best.get("filesize_approx")
        quality = f"{best.get('height', 'N/A')}p" if best.get('height') else "Unknown"

        payload = {
            "status": "success",
            "title": item.get("title"),
            "thumbnail": item.get("thumbnail"),
            "filesize": filesize,
            "quality": quality,
            "direct_download_url": direct,
        }

        # Cache the response
        _cache_set(url_key, payload)

        # Cache raw info and a simple URL map for quick subsequent redirects (optional optimization)
        try:
            keys = _cache_keys_for(item)
            _cache_set(keys["info"], item)
            cur = (_cache_get(keys["urls"]) or {}).get("value") or {}
            fid = str(best.get("format_id"))
            if fid and direct:
                cur[fid] = direct
                cur["best"] = direct
                _cache_set(keys["urls"], cur)
        except Exception:
            pass

        return JSONResponse(payload)
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@APP.get("/info")
async def fetch_video_info(url: str = Query(..., description="YouTube video URL")):
    try:
        # Check cache first
        url_key = f"map:{url}"
        cached = _cache_get(url_key)
        if cached and cached.get("value"):
            return cached["value"]

        # Extract info quickly without download; prefer progressive & skip HLS for instant links
        ydl_opts = build_ydl_opts({'skip_download': True})
        ydl_opts.setdefault("extractor_args", {}).setdefault("youtube", {})["player_client"] = "android"
        ydl_opts["extractor_args"]["youtube"]["skip"] = ["hls"]

        # Make extraction async to avoid blocking
        async def _extract_async():
            def _extract():
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    return ydl.extract_info(url, download=False)
            async with _extraction_semaphore:
                return await asyncio.to_thread(_extract)

        info = await _extract_async()
        if not info:
            raise HTTPException(status_code=502, detail="Failed to fetch info")

        # Normalize playlist vs single
        item = info["entries"][0] if (info.get("_type") == "playlist" and info.get("entries")) else info
        formats = item.get("formats") or []

        # Progressive MP4 (video+audio) only, sorted by height desc, then bitrate
        def _height(f):
            try:
                return int(f.get("height") or 0)
            except Exception:
                return 0

        video_formats = [
            {
                "quality": f"{_height(f)}p" if _height(f) else "N/A",
                "format": (f.get("ext") or "mp4").lower(),
                "filesize": f.get("filesize") or f.get("filesize_approx"),
                "direct_download_url": f.get("url"),
            }
            for f in formats if _is_progressive_mp4(f)
        ]
        video_formats.sort(key=lambda f: (int(f["quality"].replace("p", "")) if f["quality"] != "N/A" else 0, f.get("filesize") or 0), reverse=True)

        # Audio-only (instant streams like m4a/webm). "MP3" would require transcoding.
        def _abr_kbps(f):
            try:
                return int(f.get("abr") or f.get("tbr") or 0)
            except Exception:
                return 0
        audio_streams = [
            f for f in formats
            if (f.get("acodec") and f.get("acodec") != "none") and (not f.get("vcodec") or f.get("vcodec") == "none")
        ]
        audio_streams.sort(key=lambda f: (_abr_kbps(f), f.get("filesize") or f.get("filesize_approx") or 0), reverse=True)
        audio_formats = [
            {
                "bitrate": _abr_kbps(f),
                "format": (f.get("ext") or "m4a").lower(),
                "filesize": f.get("filesize") or f.get("filesize_approx"),
                "direct_download_url": f.get("url"),
            }
            for f in audio_streams
        ]

        payload = {
            "status": "success",
            "title": item.get("title"),
            "thumbnail": item.get("thumbnail"),
            "duration": item.get("duration"),
            "video_formats": video_formats,
            "audio_formats": audio_formats,
        }

        # Cache the response for future requests
        _cache_set(url_key, payload)

        # Cache raw info minimally for subsequent endpoints (optional)
        try:
            keys = _cache_keys_for(item)
            _cache_set(keys["info"], item)
        except Exception:
            pass

        return JSONResponse(payload)
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@APP.get("/universal_tailwind")
async def page_universal_tailwind(request: Request):
    return templates.TemplateResponse("universal_tailwind.html", {"request": request})


@APP.get("/")
async def page_root(request: Request):
    return templates.TemplateResponse("universal_tailwind.html", {"request": request})

@APP.get("/api/v2/{platform}/info")
async def api_v2_platform_info(platform: str, url: str = Query(...)):
    try:
        # Dynamically import the platform handler
        platform_module = importlib.import_module(f"backend.platforms.{platform}")
        
        # Call the analyze function from the platform module
        result = platform_module.analyze(url)
        
        # Map images to 'photos' for frontend consumption and ensure thumbnail present
        try:
            src_images = (result.get("jpg") or result.get("images") or [])
            photos = []
            for item in src_images:
                photos.append({
                    "url": item.get("url"),
                    "width": item.get("width"),
                    "height": item.get("height"),
                    "size": (f"{int(item.get('filesize', 0))//1024} KB" if item.get('filesize') else None)
                })
            # If no images were provided but a thumbnail exists, expose it as a photo
            if not photos and result.get("thumbnail"):
                photos = [{"url": result["thumbnail"], "width": None, "height": None, "size": None}]
            if photos:
                result["photos"] = photos
            # Ensure 'thumbnail' always exists for frontend previews
            if not result.get("thumbnail"):
                if photos:
                    result["thumbnail"] = photos[0].get("url")
                elif src_images:
                    result["thumbnail"] = src_images[0].get("url")
            # If media is video but no jpg array exists, synthesize from thumbnail
            if (result.get("media_type") == "video") and (not result.get("jpg")) and result.get("thumbnail"):
                result["jpg"] = [{
                    "url": result["thumbnail"],
                    "width": None,
                    "height": None,
                    "ext": "jpg"
                }]
        except Exception:
            pass
        
        return JSONResponse(content=result)
    except ImportError:
        raise HTTPException(status_code=404, detail=f"Platform '{platform}' not supported")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ConnectionError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        # Map obvious timeout messages to 504
        msg = str(e)
        if 'timed out' in msg or 'timeout' in msg:
            raise HTTPException(status_code=504, detail=f"Upstream timeout: {msg}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")

@APP.get("/api/redirect")
async def api_redirect(url: str = Query(...), format_id: str = Query("best")):
    # mp3 requires server-side processing
    if format_id.startswith("mp3_"):
        raise HTTPException(status_code=400, detail="MP3 requires server-side processing. Use /api/merge.")

    # Canonicalize input URL (YouTube)
    url = _normalize_input_url(url)

    # Try direct-URL cache using video id from /api/info cache
    url_key = f"map:{url}"
    cached_map = _cache_get(url_key)
    vid: Optional[str] = None
    if cached_map and cached_map.get("value"):
        vid = (cached_map["value"] or {}).get("id")
    # If we have a known video id, check cached direct URL map for that id
    if vid:
        urls_key = f"urls:{vid}"
        cached_urls = _cache_get(urls_key)
        mapping = (cached_urls or {}).get("value") or {}
        direct_cached = mapping.get(str(format_id))
        if direct_cached and await _head_ok(direct_cached):
            return RedirectResponse(url=direct_cached, status_code=302)

    # Fallback: fetch fresh info and resolve direct URL
    ydl_opts = build_ydl_opts({'skip_download': True})
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
    if not info:
        raise HTTPException(status_code=502, detail="Failed to fetch info")

    direct = _resolve_direct_url(info, format_id)
    if not direct:
        raise HTTPException(status_code=404, detail="Format not available")

    # Validate URL with HEAD (if httpx available); retry once by refetching
    if not await _head_ok(direct):
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
        direct = _resolve_direct_url(info, format_id)
        if not direct or not await _head_ok(direct):
            raise HTTPException(status_code=410, detail="Direct URL expired")

    # Cache direct URL by video id and format id for faster subsequent requests
    try:
        keys = _cache_keys_for(info)
        cur = (_cache_get(keys["urls"]) or {}).get("value") or {}
        cur[str(format_id)] = direct
        _cache_set(keys["urls"], cur)
        # Also keep the raw info cached for later endpoints
        _cache_set(keys["info"], info)
        # Cache the URL->normalized map minimally (id only) if not present
        if not (cached_map and cached_map.get("value")):
            _cache_set(url_key, {"id": info.get("id")})
    except Exception:
        pass

    # 302 to CDN. Note: filename is controlled by upstream; for custom names, use /api/passthrough
    return RedirectResponse(url=direct, status_code=302)


class DownloadRequest(BaseModel):
    url: str
    format_id: str

_tasks: Dict[str, Dict[str, Any]] = {}

def _progress_hook(d: Dict[str, Any], task_id: str) -> None:
    try:
        if (_tasks.get(task_id) or {}).get("status") == "cancelled":
            return
        st = d.get("status")
        if st == "downloading":
            _tasks[task_id] = {
                "status": "downloading",
                "progress": d.get("_percent_str", ""),
                "eta": d.get("eta"),
            }
        elif st in ("finished", "complete"):
            _tasks[task_id] = {"status": "processing", "progress": "Merging"}
    except Exception:
        pass

def _run_download_task(task_id: str, ydl_opts: Dict[str, Any], url: str) -> str:
    """Generic download task runner using yt-dlp."""
    
    ydl_opts['progress_hooks'] = [lambda d: _progress_hook(d, task_id)]

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)

    # Find the output directory from options to locate the file
    outtmpl = ydl_opts.get('outtmpl', '')
    outdir = os.path.dirname(outtmpl) if '%(' in outtmpl else DOWNLOADS_DIR

    vid = (info or {}).get("id")
    chosen: Optional[str] = None
    newest = -1
    
    # Scan the correct output directory
    scan_dir = outdir if os.path.isdir(outdir) else DOWNLOADS_DIR
    
    for f in os.listdir(scan_dir):
        if vid and vid in f:
            p = os.path.join(scan_dir, f)
            if os.path.isfile(p):
                m = os.path.getmtime(p)
                if m > newest:
                    newest = m
                    chosen = f
    
    if not chosen:
        # Fallback: find the newest file in the directory
        for f in os.listdir(scan_dir):
            p = os.path.join(scan_dir, f)
            if os.path.isfile(p):
                m = os.path.getmtime(p)
                if m > newest:
                    newest = m
                    chosen = f
        
        if not chosen:
            raise RuntimeError(f"No files found in download directory: {scan_dir}")
    
    # Return the filename relative to its platform directory
    final_path = os.path.join(os.path.basename(scan_dir), chosen)
    return final_path


async def _start_download_task(task_id: str, ydl_opts: Dict[str, Any], url: str):
    try:
        filename = await asyncio.to_thread(_run_download_task, task_id, ydl_opts, url)
        if (_tasks.get(task_id) or {}).get("status") != "cancelled":
            # Get file info for result
            full_path = os.path.join(DOWNLOADS_DIR, filename)
            filesize = os.path.getsize(full_path) if os.path.exists(full_path) else 0
            
            _tasks[task_id] = {
                "status": "finished", 
                "filename": filename, 
                "download_url": f"/download/{filename}",
                "percent": 100.0,
                "progress": "Download completed",
                "result": {
                    "path": full_path,
                    "filename": filename,
                    "filesize": filesize
                }
            }
    except Exception as e:
        if (_tasks.get(task_id) or {}).get("status") != "cancelled":
            _tasks[task_id] = {"status": "error", "error": str(e), "progress": f"Error: {str(e)}"}


@APP.post("/api/v2/{platform}/download")
async def api_v2_platform_download(platform: str, req: DownloadRequest, background: BackgroundTasks):
    """Download from any platform using universal task with cookies support.
    Note: Server-side downloads are disabled for Facebook; use instant download instead.
    """
    try:
        if platform.lower() == "facebook":
            raise HTTPException(status_code=403, detail="Server download is disabled for Facebook. Use instant download.")
        # Prefer Celery if broker is reachable; otherwise fallback to in-process background task
        task_id: Optional[str] = None
        try:
            task = universal_download_task.delay(req.url, req.format_id, platform)
            task_id = task.id
            return {"task_id": task_id}
        except Exception:
            # Fallback: run with yt-dlp directly in background (no Celery required)
            ydl_opts = build_ydl_opts(platform=platform)
            outdir = DOWNLOADS_DIR
            # Ensure sensible outtmpl
            ydl_opts.setdefault('outtmpl', os.path.join(outdir, f"{platform}-%(uploader)s-%(title)s [%(id)s].%(ext)s"))
            # Format selection similar to universal task
            fmt = req.format_id
            if fmt == 'best':
                ydl_opts['format'] = 'best[ext=mp4]/best'
            elif fmt == 'audio' or str(fmt).startswith('mp3_'):
                ydl_opts['format'] = 'bestaudio/best'
                ydl_opts['postprocessors'] = [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': str(getattr(req, 'tbr', 192))
                }]
            else:
                ydl_opts['format'] = fmt
            # Create a local task id and start
            task_id = str(uuid.uuid4())
            _tasks[task_id] = {"status": "queued", "progress": "Queued"}
            background.add_task(_start_download_task, task_id, ydl_opts, req.url)
            return {"task_id": task_id, "fallback": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Download failed: {e}")


# v2 instant streaming endpoint (compatibility for frontend)
@APP.get("/api/v2/{platform}/instant")
@APP.head("/api/v2/{platform}/instant")
async def api_v2_instant(platform: str, url: str = Query(...), format_id: str = Query("best"), filename: Optional[str] = Query(None)):
    """
    Instant download via streaming/proxy for any supported platform.
    - Tries progressive/direct stream first (/api/stream)
    - Falls back to on-the-fly merge for video-only formats (/api/stream_merge)
    - For MP3 (mp3_XXX), streams on-the-fly conversion via /api/stream_mp3
    """
    # MP3 instant: stream on-the-fly audio transcode
    if str(format_id).startswith("mp3_"):
        return await api_stream_mp3(url=url, format_id=format_id, filename=filename)
    try:
        # Attempt direct/progressive streaming
        return await api_stream(url=url, format_id=format_id, filename=filename)
    except HTTPException as e:
        # If format not progressive or expired, try merge for video-only
        if e.status_code in (404, 410):
            return await api_stream_merge(url=url, format_id=format_id, filename=filename)
        raise


@APP.get("/api/v2/sign")
async def api_sign(
    platform: str = Query(...),
    url: str = Query(...),
    format_id: str = Query(...),
    ttl: int = Query(3600, ge=60, le=86400),
    filename: Optional[str] = Query(None)
):
    """Generate a signed download link."""
    try:
        # Canonicalize input URL (YouTube)
        url = _normalize_input_url(url)
        payload = {
            "platform": platform,
            "url": url,
            "format_id": format_id,
            "filename": filename
        }
        token = make_token(SECRET_KEY, payload, ttl)
        return JSONResponse({
            "signed_url": f"/dl?token={token}",
            "expires_in": ttl,
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)

@APP.get("/dl")
async def dl_signed(token: str = Query(...)):
    """Resolve a signed download link."""
    try:
        payload = verify_token(SECRET_KEY, token)
        platform = payload["platform"]
        url = _normalize_input_url(payload["url"])  # Canonicalize for consistency
        format_id = payload["format_id"]
        filename = payload.get("filename")

        platform_module = importlib.import_module(f"backend.platforms.{platform}")
        info = platform_module.analyze(url)
        
        direct_url = None
        for f in info.get('mp4', []) + info.get('mp3', []):
            if f.get('format_id') == format_id:
                direct_url = f.get('url')
                break

        if not direct_url:
            raise HTTPException(status_code=404, detail="Format not found or direct URL unavailable")

        return RedirectResponse(url=direct_url)

    except ValueError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@APP.get("/api/v2/task/{task_id}")
async def api_v2_task_status(task_id: str):
    # Prefer Celery/Redis-based progress if available, but be resilient if Redis/Celery down
    progress = {}
    try:
        progress = get_progress(task_id) or {}
    except Exception:
        progress = {}
    try:
        ar = AsyncResult(task_id, app=celery)
        state = getattr(ar, "state", None)
    except Exception:
        ar = None
        state = None

    if ar and state and state != "PENDING":
        payload = {
            "task_id": task_id,
            "state": state,
            "status": progress.get("status") or (state.lower() if state else "pending"),
            "percent": progress.get("percent"),
            "eta": progress.get("eta"),
            "detail": progress.get("detail"),
        }
        if state == "SUCCESS":
            try:
                r = ar.result or {}
                payload["result"] = {
                    "path": r.get("path"),
                    "id": r.get("id"),
                    "title": r.get("title"),
                    "ext": r.get("ext"),
                    "filesize": r.get("filesize"),
                }
            except Exception:
                pass
        elif state == "FAILURE":
            payload.setdefault("status", "error")
        return payload

    # Fallback to in-process task map (dev/local mode)
    try:
        data = _tasks.get(task_id)
        if data:
            return data
    except Exception:
        pass

    # If everything else fails, report a safe pending state
    return {"task_id": task_id, "state": "PENDING", **({} if not progress else progress)}


@APP.delete("/api/v2/task/{task_id}")
async def api_v2_task_cancel(task_id: str):
    if task_id not in _tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    # Soft cancel: mark as cancelled, the background thread may still finish but UI will stop polling
    _tasks[task_id] = {"status": "cancelled"}
    return {"status": "cancelled"}


@APP.get("/download/{filename}")
async def download_file(filename: str):
    path = os.path.join(DOWNLOADS_DIR, filename)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path, filename=filename, media_type="application/octet-stream")


@APP.get("/api/passthrough")
async def api_passthrough(url: str = Query(...), filename: Optional[str] = None):
    if not httpx:
        raise HTTPException(status_code=500, detail="httpx not installed on server")
    # Forward range for resumable downloads (basic): browsers will send Range; advanced handling omitted for brevity
    try:
        # Use a short-lived client for HEAD to detect size/type
        total = None
        content_type = "application/octet-stream"
        async with httpx.AsyncClient(timeout=None, follow_redirects=True) as _client:
            head = await _client.head(url)
            if head.status_code >= 400:
                raise HTTPException(status_code=head.status_code, detail="Source unavailable")
            total = head.headers.get("Content-Length")
            content_type = head.headers.get("Content-Type", "application/octet-stream")

        async def streamer():
            # Keep the client open for the entire stream
            try:
                async with httpx.AsyncClient(timeout=None, follow_redirects=True) as client:
                    async with client.stream("GET", url) as r:
                        r.raise_for_status()
                        async for chunk in r.aiter_bytes(1024 * 64):
                            yield chunk
            except Exception:
                # Stop streaming gracefully to avoid unhandled TaskGroup errors
                return

        resp = StreamingResponse(streamer(), media_type=content_type)
        if total:
            resp.headers["Content-Length"] = total
        resp.headers["Accept-Ranges"] = "bytes"
        if filename:
            resp.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
        return resp
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@APP.get("/api/stream")
async def api_stream(url: str = Query(...), format_id: str = Query("best"), filename: Optional[str] = None):
    """Stream a direct progressive format instantly (audio+video already combined).
    For video-only formats, use /api/stream_merge instead.
    """
    if format_id.startswith("mp3_"):
        raise HTTPException(status_code=400, detail="MP3 requires server-side processing. Use /api/merge.")

    # Canonicalize input URL (YouTube)
    url = _normalize_input_url(url)

    # Try cached direct URL first (via URL->video id map, then format id mapping)
    direct: Optional[str] = None
    url_key = f"map:{url}"
    cached_map = _cache_get(url_key)
    vid: Optional[str] = None
    if cached_map and cached_map.get("value"):
        vid = (cached_map["value"] or {}).get("id")
    if vid:
        urls_key = f"urls:{vid}"
        cached_urls = _cache_get(urls_key)
        mapping = (cached_urls or {}).get("value") or {}
        direct_cached = mapping.get(str(format_id))
        if direct_cached and await _head_ok(direct_cached):
            direct = direct_cached

    # Fallback: fetch fresh info and resolve direct URL
    if not direct:
        ydl_opts = build_ydl_opts({'skip_download': True})
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
        if not info:
            raise HTTPException(status_code=502, detail="Failed to fetch info")

        direct = _resolve_direct_url(info, format_id)
        if not direct:
            raise HTTPException(status_code=404, detail="Format not available or not progressive")

        # Validate URL with HEAD (if httpx available); retry once by refetching
        if not await _head_ok(direct):
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
            direct = _resolve_direct_url(info, format_id)
            if not direct or not await _head_ok(direct):
                raise HTTPException(status_code=410, detail="Direct URL expired")

        # Cache direct URL by video id and format id
        try:
            keys = _cache_keys_for(info)
            cur = (_cache_get(keys["urls"]) or {}).get("value") or {}
            cur[str(format_id)] = direct
            _cache_set(keys["urls"], cur)
            _cache_set(keys["info"], info)
            if not (cached_map and cached_map.get("value")):
                _cache_set(url_key, {"id": info.get("id")})
        except Exception:
            pass

    # Stream the resolved URL
    if not httpx:
        raise HTTPException(status_code=500, detail="httpx not installed on server")

    try:
        # Use a short-lived client for HEAD to detect size/type
        total = None
        content_type = "application/octet-stream"
        # Prepare headers (helps avoid 403 on some CDNs)
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            referer = f"{parsed.scheme}://{parsed.netloc}/" if parsed.scheme and parsed.netloc else ""
        except Exception:
            referer = ""
        ua = os.environ.get('USER_AGENT', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36')
        accept_lang = os.environ.get('ACCEPT_LANGUAGE', 'en-US,en;q=0.9')
        headers = {"User-Agent": ua, "Accept-Language": accept_lang, "Accept": "*/*"}
        if referer:
            headers["Referer"] = referer
        async with httpx.AsyncClient(timeout=None, follow_redirects=True) as _client:
            head = await _client.head(direct, headers=headers)
            if head.status_code >= 400:
                raise HTTPException(status_code=head.status_code, detail="Source unavailable")
            total = head.headers.get("Content-Length")
            content_type = head.headers.get("Content-Type", "application/octet-stream")

        async def streamer():
            # Keep the client open for the entire stream
            try:
                async with httpx.AsyncClient(timeout=None, follow_redirects=True) as client:
                    async with client.stream("GET", direct, headers=headers) as r:
                        r.raise_for_status()
                        async for chunk in r.aiter_bytes(1024 * 64):
                            yield chunk
            except Exception:
                # Stop streaming gracefully to avoid unhandled TaskGroup errors
                return

        resp = StreamingResponse(streamer(), media_type=content_type)
        if total:
            resp.headers["Content-Length"] = total
        resp.headers["Accept-Ranges"] = "bytes"
        if filename:
            resp.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
        return resp
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@APP.get("/api/stream_mp3")
async def api_stream_mp3(url: str = Query(...), format_id: str = Query(...), filename: Optional[str] = None):
    """Instant MP3: stream on-the-fly conversion from bestaudio to MP3 at requested bitrate.
    format_id: mp3_128 | mp3_192 | mp3_320
    """
    # Parse bitrate
    import re as _re
    m = _re.match(r"(?i)^mp3[_-]?(\d{2,3})$", str(format_id or ""))
    bitrate = int(m.group(1)) if m else 192
    bitrate = max(32, min(320, bitrate))

    # Canonicalize input URL (YouTube)
    url = _normalize_input_url(url)

    # Resolve bestaudio direct URL
    ydl_opts = build_ydl_opts({'skip_download': True})
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
    if not info:
        raise HTTPException(status_code=502, detail="Failed to fetch info")

    item = info["entries"][0] if (info.get("_type") == "playlist" and info.get("entries")) else info
    fmts = item.get("formats") or []
    audio_streams = [
        f for f in fmts
        if (f.get("acodec") and f.get("acodec") != "none") and (not f.get("vcodec") or f.get("vcodec") == "none")
    ]
    if not audio_streams:
        raise HTTPException(status_code=404, detail="No audio-only stream available")

    # Prefer higher abr/tbr
    def _abr(f):
        try:
            return int(f.get("abr") or f.get("tbr") or 0)
        except Exception:
            return 0
    audio_streams.sort(key=lambda f: (_abr(f), f.get("filesize") or f.get("filesize_approx") or 0), reverse=True)
    best_audio = audio_streams[0]
    audio_url = best_audio.get("url")

    # Build filename
    if not filename:
        base = item.get("title") or item.get("id") or "audio"
        safe = str(base).replace('/', ' ').replace('\\', ' ').replace(':', ' ').strip()
        filename = f"{safe} - {bitrate}kbps.mp3"

    # Prepare headers
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        referer = f"{parsed.scheme}://{parsed.netloc}/" if parsed.scheme and parsed.netloc else ""
    except Exception:
        referer = ""
    ua = os.environ.get('USER_AGENT', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36')
    accept_lang = os.environ.get('ACCEPT_LANGUAGE', 'en-US,en;q=0.9')
    header_str = f"User-Agent: {ua}\r\nAccept-Language: {accept_lang}\r\nAccept: */*\r\n" + (f"Referer: {referer}\r\n" if referer else "")

    import subprocess

    # ffmpeg pipeline: read audio input -> transcode to MP3 CBR bitrate, faststart-friendly output
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error",
        "-nostdin",
        "-headers", header_str, "-reconnect", "1", "-reconnect_streamed", "1", "-reconnect_delay_max", "2",
        "-i", audio_url,
        "-vn", "-c:a", "libmp3lame", "-b:a", f"{bitrate}k",
        "-f", "mp3", "pipe:1"
    ]

    try:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        async def ffmpeg_streamer():
            try:
                while True:
                    # Check if process has failed before reading
                    if process.poll() is not None and process.poll() != 0:
                        # Process failed, read error and raise
                        err = process.stderr.read().decode(errors='ignore') if process.stderr else ''
                        raise HTTPException(status_code=500, detail=f"ffmpeg failed ({process.poll()}) {err[:200]}")

                    try:
                        chunk = await asyncio.get_event_loop().run_in_executor(None, process.stdout.read, 64 * 1024)
                        if not chunk:
                            break
                        yield chunk
                    except Exception as e:
                        # Handle read errors gracefully
                        err = process.stderr.read().decode(errors='ignore') if process.stderr else str(e)
                        raise HTTPException(status_code=500, detail=f"Stream read failed: {err[:200]}")
            finally:
                try:
                    process.stdout.close()
                except Exception:
                    pass
                rc = process.wait(timeout=5)
                if rc != 0:
                    err = process.stderr.read().decode(errors='ignore') if process.stderr else ''
                    raise HTTPException(status_code=500, detail=f"ffmpeg failed ({rc}) {err[:200]}")

        headers = {"Content-Disposition": f"attachment; filename=\"{filename}\""}
        return StreamingResponse(ffmpeg_streamer(), media_type="audio/mpeg", headers=headers)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@APP.get("/api/stream_merge")
async def api_stream_merge(url: str = Query(...), format_id: str = Query(...), filename: Optional[str] = None):
    """Start an instant, on-the-fly merge for video-only formats with bestaudio.
    The browser download starts immediately while ffmpeg muxes in real-time.
    """
    # Canonicalize input URL (YouTube)
    url = _normalize_input_url(url)

    # Resolve raw info to get chosen video-only URL and bestaudio URL
    ydl_opts = build_ydl_opts({'skip_download': True})
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
    if not info:
        raise HTTPException(status_code=502, detail="Failed to fetch info")

    # Flatten playlist if needed
    item = info["entries"][0] if (info.get("_type") == "playlist" and info.get("entries")) else info
    fmts = item.get("formats") or []

    # Pick the requested video-only by format_id
    video_url = None
    video_fmt = None
    for f in fmts:
        if str(f.get("format_id")) == str(format_id):
            # Ensure it is video-only
            if (f.get("vcodec") and f.get("vcodec") != "none") and (not f.get("acodec") or f.get("acodec") == "none"):
                video_url = f.get("url")
                video_fmt = f
            break
    if not video_url:
        raise HTTPException(status_code=404, detail="Requested format must be video-only")

    # Pick bestaudio (m4a/webm) by highest abr/tbr
    audio_streams = [
        f for f in fmts
        if (f.get("acodec") and f.get("acodec") != "none") and (not f.get("vcodec") or f.get("vcodec") == "none")
    ]
    if not audio_streams:
        raise HTTPException(status_code=404, detail="No audio stream available to merge")

    def _abr(f):
        try:
            return int(f.get("abr") or f.get("tbr") or 0)
        except Exception:
            return 0
    audio_streams.sort(key=lambda f: (_abr(f), f.get("filesize") or f.get("filesize_approx") or 0), reverse=True)
    best_audio = audio_streams[0]
    audio_url = best_audio.get("url")
    audio_ext = (best_audio.get("ext") or "m4a").lower()

    # Stream with ffmpeg passthrough (copy codecs)
    if not filename:
        base = item.get("title") or item.get("id") or "video"
        safe = str(base).replace('/', ' ').replace('\\', ' ').replace(':', ' ').strip()
        filename = f"{safe}.mp4"

    import subprocess
    from shlex import quote as _q

    # Build ffmpeg command (support non-seekable MP4 and incompatible audio)
    audio_codec = (best_audio.get("acodec") or "").lower()
    needs_transcode = ("opus" in audio_codec) or ("vorbis" in audio_codec) or (audio_ext not in ("m4a", "mp4", "aac", "mp3"))

    # Prepare HTTP headers for inputs (helps avoid 403 on some CDNs)
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        referer = f"{parsed.scheme}://{parsed.netloc}/" if parsed.scheme and parsed.netloc else ""
    except Exception:
        referer = ""
    ua = os.environ.get('USER_AGENT', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36')
    accept_lang = os.environ.get('ACCEPT_LANGUAGE', 'en-US,en;q=0.9')
    header_str = f"User-Agent: {ua}\r\nAccept-Language: {accept_lang}\r\nAccept: */*\r\n" + (f"Referer: {referer}\r\n" if referer else "")

    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error",
        "-nostdin",
        # Input 0: video
        "-headers", header_str, "-reconnect", "1", "-reconnect_streamed", "1", "-reconnect_delay_max", "2",
        "-i", video_url,
        # Input 1: audio
        "-headers", header_str, "-reconnect", "1", "-reconnect_streamed", "1", "-reconnect_delay_max", "2",
        "-i", audio_url,
    ]

    if needs_transcode:
        # Copy video, transcode audio to AAC for MP4 compatibility
        cmd += ["-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k"]
    else:
        # Direct stream copy when audio is already MP4-compatible
        cmd += ["-map", "0:v:0", "-map", "1:a:0", "-c", "copy"]

    # Use fragmented MP4 for non-seekable streaming over HTTP (fast start while streaming)
    # +frag_keyframe makes moof fragments at keyframes; +empty_moov allows writing header first
    cmd += ["-movflags", "+frag_keyframe+empty_moov", "-shortest", "-f", "mp4", "pipe:1"]

    try:
        # Spawn process and stream stdout to client
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        async def ffmpeg_streamer():
            try:
                while True:
                    # Check if process has failed before reading
                    if process.poll() is not None and process.poll() != 0:
                        # Process failed, read error and raise
                        err = process.stderr.read().decode(errors='ignore') if process.stderr else ''
                        raise HTTPException(status_code=500, detail=f"ffmpeg failed ({process.poll()}) {err[:200]}")

                    try:
                        chunk = await asyncio.get_event_loop().run_in_executor(None, process.stdout.read, 64 * 1024)
                        if not chunk:
                            break
                        yield chunk
                    except Exception as e:
                        # Handle read errors gracefully
                        err = process.stderr.read().decode(errors='ignore') if process.stderr else str(e)
                        raise HTTPException(status_code=500, detail=f"Stream read failed: {err[:200]}")
            finally:
                try:
                    process.stdout.close()
                except Exception:
                    pass
                rc = process.wait(timeout=5)
                if rc != 0:
                    # Surface ffmpeg error
                    err = process.stderr.read().decode(errors='ignore') if process.stderr else ''
                    raise HTTPException(status_code=500, detail=f"ffmpeg failed ({rc}) {err[:200]}")

        headers = {"Content-Disposition": f"attachment; filename=\"{filename}\""}
        return StreamingResponse(ffmpeg_streamer(), media_type="video/mp4", headers=headers)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@APP.post("/api/download")
async def api_download_post(req: DownloadRequest, background: BackgroundTasks, _: None = Depends(require_api_key)):
    """
    POST endpoint for downloads - returns task_id for progress tracking
    Uses universal download task with automatic platform detection and cookies
    """
    try:
        # Use universal download task with auto-detection
        task = universal_download_task.delay(req.url, req.format_id)
        task_id = task.id
        
        return {"task_id": task_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Download failed: {e}")


@APP.get("/api/download")
async def api_download(url: str = Query(...), format_id: str = Query("best"), filename: Optional[str] = None, _: None = Depends(require_api_key)):
    """
    Resolve direct CDN URL (with cache) and stream through server while setting a clean filename.
    Falls back back to 302 redirect if httpx is unavailable.
    """
    # mp3 requires server-side processing
    if format_id.startswith("mp3_"):
        raise HTTPException(status_code=400, detail="MP3 requires server-side processing. Use /api/merge.")

    # Canonicalize input URL (YouTube)
    url = _normalize_input_url(url)

    # If httpx missing, degrade to simple redirect
    if not httpx:
        return await api_redirect(url=url, format_id=format_id)

    # Try direct-URL cache using video id from /api/info cache
    url_key = f"map:{url}"
    cached_map = _cache_get(url_key)
    vid: Optional[str] = None
    if cached_map and cached_map.get("value"):
        vid = (cached_map["value"] or {}).get("id")
    if vid:
        urls_key = f"urls:{vid}"
        cached_urls = _cache_get(urls_key)
        mapping = (cached_urls or {}).get("value") or {}
        direct_cached = mapping.get(str(format_id))
        if direct_cached and await _head_ok(direct_cached):
            return await api_passthrough(url=direct_cached, filename=filename)

    # Fallback: fetch fresh info and resolve direct URL
    ydl_opts = build_ydl_opts({'skip_download': True})
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
    if not info:
        raise HTTPException(status_code=502, detail="Failed to fetch info")

    direct = _resolve_direct_url(info, format_id)
    if not direct:
        raise HTTPException(status_code=404, detail="Format not available")

    # Validate URL with HEAD; retry once
    if not await _head_ok(direct):
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
        direct = _resolve_direct_url(info, format_id)
        if not direct or not await _head_ok(direct):
            raise HTTPException(status_code=410, detail="Direct URL expired")

    # Cache resolved direct URL
    try:
        keys = _cache_keys_for(info)
        cur = (_cache_get(keys["urls"]) or {}).get("value") or {}
        cur[str(format_id)] = direct
        _cache_set(keys["urls"], cur)
        _cache_set(keys["info"], info)
        if not (cached_map and cached_map.get("value")):
            _cache_set(url_key, {"id": info.get("id")})
    except Exception:
        pass

    return await api_passthrough(url=direct, filename=filename)


@APP.get("/ui", response_class=HTMLResponse)
async def ui():
    # Minimal test UI that calls /api/info then redirects via /api/redirect
    return """
<!doctype html>
<html>
<head>
  <meta charset='utf-8'>
  <title>Downloader UI</title>
  <style>
    body { font-family: system-ui, sans-serif; max-width: 720px; margin: 40px auto; }
    input, button { padding: 8px 12px; font-size: 16px; }
    .fmt { padding: 6px 8px; border: 1px solid #ddd; margin: 6px 0; display:flex; justify-content:space-between; align-items:center; }
  </style>
</head>
<body>
  <h1>Downloader</h1>
  <input id="url" placeholder="Paste YouTube URL" style="width: 100%" />
  <button id="go">Analyze</button>
  <div id="list"></div>
  <script>
    const btn = document.getElementById('go');
    const list = document.getElementById('list');
    btn.onclick = async () => {
      const url = document.getElementById('url').value.trim();
      if (!url) return alert('Enter a URL');
      list.innerHTML = 'Loading...';
      const r = await fetch('/api/info?url=' + encodeURIComponent(url));
      if (!r.ok) return list.innerHTML = 'Error fetching info';
      const info = await r.json();
      list.innerHTML = '';
      (info.formats || []).forEach(f => {
        const row = document.createElement('div');
        row.className = 'fmt';
        const name = `${f.quality || ''} ${f.ext || ''} ${f.filesize_mb ? '(' + f.filesize_mb + ' MB)' : ''}`;
        row.innerHTML = `<span>${name}</span>`;
        const a = document.createElement('a');
        a.textContent = 'Download';
        a.href = `/api/redirect?url=${encodeURIComponent(url)}&format_id=${encodeURIComponent(f.format_id)}`;
        row.appendChild(a);
        list.appendChild(row);
      });
    };
  </script>
</body>
</html>
"""


@APP.get("/universal_tailwind", response_class=HTMLResponse)
async def universal_tailwind_page(request: Request):
    # Render the Tailwind UI template with sane defaults for ads params
    context = {
        "request": request,
        "adsense_enabled": False,
        "adsense_client": None,
        "adsense_header_slot": None,
        "adsense_inline_slot": None,
        "adsense_footer_slot": None,
        "gtag_id": None,
    }
    return templates.TemplateResponse("universal_tailwind.html", context)


# Platform-specific downloader pages
@APP.get("/youtube-downloader", response_class=HTMLResponse)
async def youtube_downloader_page(request: Request):
    context = {
        "request": request,
        "default_platform": "youtube",
        "adsense_enabled": False,
        "adsense_client": None,
        "adsense_header_slot": None,
        "adsense_inline_slot": None,
        "adsense_footer_slot": None,
        "gtag_id": None,
    }
    return templates.TemplateResponse("universal_tailwind.html", context)

@APP.get("/instagram-downloader", response_class=HTMLResponse)
async def instagram_downloader_page(request: Request):
    context = {
        "request": request,
        "default_platform": "instagram",
        "adsense_enabled": False,
        "adsense_client": None,
        "adsense_header_slot": None,
        "adsense_inline_slot": None,
        "adsense_footer_slot": None,
        "gtag_id": None,
    }
    return templates.TemplateResponse("universal_tailwind.html", context)

@APP.get("/facebook-downloader", response_class=HTMLResponse)
async def facebook_downloader_page(request: Request):
    context = {
        "request": request,
        "default_platform": "facebook",
        "adsense_enabled": False,
        "adsense_client": None,
        "adsense_header_slot": None,
        "adsense_inline_slot": None,
        "adsense_footer_slot": None,
        "gtag_id": None,
    }
    return templates.TemplateResponse("universal_tailwind.html", context)

@APP.get("/tiktok-downloader", response_class=HTMLResponse)
async def tiktok_downloader_page(request: Request):
    context = {
        "request": request,
        "default_platform": "tiktok",
        "adsense_enabled": False,
        "adsense_client": None,
        "adsense_header_slot": None,
        "adsense_inline_slot": None,
        "adsense_footer_slot": None,
        "gtag_id": None,
    }
    return templates.TemplateResponse("universal_tailwind.html", context)

@APP.get("/twitter-downloader", response_class=HTMLResponse)
async def twitter_downloader_page(request: Request):
    context = {
        "request": request,
        "default_platform": "twitter",
        "adsense_enabled": False,
        "adsense_client": None,
        "adsense_header_slot": None,
        "adsense_inline_slot": None,
        "adsense_footer_slot": None,
        "gtag_id": None,
    }
    return templates.TemplateResponse("universal_tailwind.html", context)

@APP.get("/pinterest-downloader", response_class=HTMLResponse)
async def pinterest_downloader_page(request: Request):
    context = {
        "request": request,
        "default_platform": "pinterest",
        "adsense_enabled": False,
        "adsense_client": None,
        "adsense_header_slot": None,
        "adsense_inline_slot": None,
        "adsense_footer_slot": None,
        "gtag_id": None,
    }
    return templates.TemplateResponse("universal_tailwind.html", context)

@APP.get("/snapchat-downloader", response_class=HTMLResponse)
async def snapchat_downloader_page(request: Request):
    context = {
        "request": request,
        "default_platform": "snapchat",
        "adsense_enabled": False,
        "adsense_client": None,
        "adsense_header_slot": None,
        "adsense_inline_slot": None,
        "adsense_footer_slot": None,
        "gtag_id": None,
    }
    return templates.TemplateResponse("universal_tailwind.html", context)

@APP.get("/linkedin-downloader", response_class=HTMLResponse)
async def linkedin_downloader_page(request: Request):
    context = {
        "request": request,
        "default_platform": "linkedin",
        "adsense_enabled": False,
        "adsense_client": None,
        "adsense_header_slot": None,
        "adsense_inline_slot": None,
        "adsense_footer_slot": None,
        "gtag_id": None,
    }
    return templates.TemplateResponse("universal_tailwind.html", context)

@APP.get("/reddit-downloader", response_class=HTMLResponse)
async def reddit_downloader_page(request: Request):
    context = {
        "request": request,
        "default_platform": "reddit",
        "adsense_enabled": False,
        "adsense_client": None,
        "adsense_header_slot": None,
        "adsense_inline_slot": None,
        "adsense_footer_slot": None,
        "gtag_id": None,
    }
    return templates.TemplateResponse("universal_tailwind.html", context)


@APP.get("/cookies", response_class=HTMLResponse)
async def cookies_manager_page(request: Request):
    """Serve the cookies management interface"""
    context = {"request": request}
    return templates.TemplateResponse("cookies_manager.html", context)


@APP.get("/progress_demo", response_class=HTMLResponse)
async def progress_demo_page(request: Request):
    """Colorful Progress Bars Demo Page"""
    context = {"request": request}
    return templates.TemplateResponse("progress_demo.html", context)


@APP.get("/progress_test", response_class=HTMLResponse)
async def progress_test_page(request: Request):
    """Progress Manager Test Page"""
    context = {"request": request}
    return templates.TemplateResponse("progress_test.html", context)


# Task queue endpoints (Celery)
@APP.post("/api/tasks/youtube_download")
async def api_tasks_youtube_download(
    url: str = Body(..., embed=True),
    format_id: str = Body("best", embed=True)
):
    try:
        res = download_task.delay(url, format_id)
        return {"task_id": res.id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Queue failed: {e}")

@APP.get("/api/task_status")
async def api_task_status(task_id: str = Query(...)):
    progress = get_progress(task_id) or {}
    ar = AsyncResult(task_id, app=celery)
    state = ar.state if ar else "PENDING"
    payload = {
        "task_id": task_id,
        "state": state,
        "status": progress.get("status") or state.lower(),
        "percent": progress.get("percent"),
        "eta": progress.get("eta"),
        "detail": progress.get("detail"),
    }
    if ar and state == "SUCCESS":
        try:
            r = ar.result or {}
            payload["result"] = {
                "path": r.get("path"),
                "id": r.get("id"),
                "title": r.get("title"),
                "ext": r.get("ext"),
                "filesize": r.get("filesize"),
            }
        except Exception:
            pass
    return JSONResponse(payload)

# --- Compatibility endpoints expected by universal_tailwind frontend ---
from pydantic import BaseModel

class AnalyzeBody(BaseModel):
    url: str

@APP.post("/api/{platform}/analyze")
async def api_platform_analyze(platform: str, body: AnalyzeBody):
    try:
        platform_module = importlib.import_module(f"backend.platforms.{platform}")
        result = platform_module.analyze(body.url)
        # Ensure images key exists for UI
        if isinstance(result, dict) and "images" not in result:
            imgs = result.get("jpg") or []
            if imgs:
                result["images"] = imgs
        return JSONResponse(content=result)
    except ImportError:
        raise HTTPException(status_code=404, detail=f"Platform '{platform}' not supported")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analyze failed: {e}")

class MergeBody(BaseModel):
    url: str
    video_format_id: Optional[str] = None
    mp3_bitrate: Optional[int] = None

# Simple platform detector using URL_PATTERNS in platform modules
import re as _re

def _detect_platform_from_url(url: str) -> str:
    for name in ("youtube", "instagram", "facebook", "tiktok", "twitter", "pinterest", "snapchat"):
        try:
            mod = importlib.import_module(f"backend.platforms.{name}")
            patterns = getattr(mod, "URL_PATTERNS", [])
            if any(p.search(url or "") for p in patterns):
                return name
        except Exception:
            continue
    return "youtube"

@APP.post("/api/merge")
async def api_merge(body: MergeBody, background: BackgroundTasks):
    platform = _detect_platform_from_url(body.url)
    try:
        mod = importlib.import_module(f"backend.platforms.{platform}")
        if body.mp3_bitrate:
            fmt = f"mp3_{int(body.mp3_bitrate)}"
        else:
            fmt = str(body.video_format_id or "best")
        # Prefer Celery for heavy work; fall back to in-process background task
        try:
            res = download_task.delay(body.url, fmt)
            return {"task_id": res.id}
        except Exception:
            ydl_opts, _ = mod.prepare_download(body.url, fmt)
            task_id = str(int(time.time() * 1000))
            _tasks[task_id] = {"status": "queued", "progress": "Starting"}
            background.add_task(_start_download_task, task_id, ydl_opts, body.url)
            return {"task_id": task_id}
    except ImportError:
        raise HTTPException(status_code=404, detail=f"Platform '{platform}' not supported")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Merge failed: {e}")

@APP.get("/api/merge/{task_id}")
async def api_merge_status(task_id: str):
    # First check in-memory tasks (for background tasks)
    data = _tasks.get(task_id)
    if data:
        return {
            "task_id": task_id,
            "state": data.get("status", "PENDING").upper(),
            "status": data.get("status", "pending"),
            "percent": data.get("percent"),
            "eta": data.get("eta"),
            "detail": data.get("progress", ""),
            "result": data.get("result") if data.get("status") == "finished" else None
        }
    
    # Then check Celery tasks (if available)
    try:
        progress = get_progress(task_id) or {}
        ar = AsyncResult(task_id, app=celery)
        if ar and ar.state != "PENDING":
            payload = {
                "task_id": task_id,
                "state": ar.state,
                "status": progress.get("status") or ar.state.lower(),
                "percent": progress.get("percent"),
                "eta": progress.get("eta"),
                "detail": progress.get("detail"),
            }
            if ar.state == "SUCCESS":
                try:
                    r = ar.result or {}
                    payload["result"] = {
                        "path": r.get("path"),
                        "id": r.get("id"),
                        "title": r.get("title"),
                        "ext": r.get("ext"),
                        "filesize": r.get("filesize"),
                    }
                except Exception:
                    pass
            return payload
    except Exception:
        pass
    
    # Task not found
    raise HTTPException(status_code=404, detail="Task not found")

@APP.delete("/api/merge/{task_id}")
async def api_merge_cancel(task_id: str):
    # Best-effort cancel: for Celery tasks you can revoke, for in-process we mark as cancelled
    try:
        ar = AsyncResult(task_id, app=celery)
        if ar and ar.state not in ("SUCCESS", "FAILURE"):
            ar.revoke(terminate=False)
    except Exception:
        pass
    if task_id in _tasks:
        _tasks[task_id] = {"status": "cancelled"}
    return {"status": "cancelled"}

@APP.post("/api/{platform}/download_images_zip")
async def api_download_images_zip(platform: str, payload: Dict[str, Any] = Body(...)):
    url = payload.get("url", "")
    indices = payload.get("indices") or []
    filenames = payload.get("filenames") or []
    try:
        platform_module = importlib.import_module(f"backend.platforms.{platform}")
        info = platform_module.analyze(url)
        images = (info.get("images") or info.get("jpg") or [])
        # select images
        selected = []
        for i in indices:
            try:
                ii = int(i)
                if 0 <= ii < len(images):
                    selected.append({"idx": ii, "data": images[ii]})
            except Exception:
                continue
        if not selected:
            raise HTTPException(status_code=400, detail="No valid images selected")
        import io as _io, zipfile as _zipfile, requests as _requests, json as _json, datetime as _dt
        mem = _io.BytesIO()
        with _zipfile.ZipFile(mem, 'w', compression=_zipfile.ZIP_DEFLATED) as zf:
            # 1) Write info.json with metadata
            metadata = {
                "title": info.get("title") or info.get("id") or "Media",
                "uploader": info.get("uploader") or info.get("author") or "Unknown",
                "url": url,
                "platform": platform,
                "timestamp": _dt.datetime.utcnow().isoformat() + "Z",
                "items_count": len(images),
                "selected_indices": [s["idx"] for s in selected],
            }
            zf.writestr("info.json", _json.dumps(metadata, ensure_ascii=False, indent=2))

            # 2) Write cover.jpg from best thumbnail if available
            cover_url = info.get("thumbnail")
            if not cover_url and images:
                # fallback to first image URL
                cover_url = images[0].get("url")
            if cover_url:
                try:
                    c = _requests.get(cover_url, timeout=20)
                    if c.ok:
                        zf.writestr("cover.jpg", c.content)
                except Exception:
                    pass

            # 3) Add each selected image
            for idx, entry in enumerate(selected):
                img = entry["data"]
                ext = (img.get("ext") or "jpg").lower()
                name = None
                if idx < len(filenames) and filenames[idx]:
                    name = filenames[idx].strip()
                if not name:
                    # use original index from 'indices' for label if available
                    label = indices[idx] if idx < len(indices) else entry["idx"]
                    name = f"image-{label}.{ext}"
                resp = _requests.get(img.get("url"), timeout=30)
                resp.raise_for_status()
                zf.writestr(name, resp.content)
        mem.seek(0)
        headers = {"Content-Disposition": 'attachment; filename="images.zip"'}
        return StreamingResponse(mem, media_type="application/zip", headers=headers)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ZIP failed: {e}")


@APP.get("/instagram/debug")
async def instagram_debug_endpoint(url: str = Query(...)):
    """Debug Instagram thumbnail and media extraction."""
    try:
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


@APP.get("/health")
async def health():
    return {"status": "ok"}


# ============================================================================
# COOKIES & AUTHENTICATION MANAGEMENT
# ============================================================================

@APP.post("/api/auth/cookies/upload")
async def upload_cookies(platform: str, session_name: str = "default", cookies_content: str = Body(...)):
    """Upload cookies for a platform"""
    try:
        result = auth_manager.save_cookies(platform, cookies_content, session_name)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload cookies: {e}")

@APP.get("/api/auth/cookies/sessions")
async def list_cookie_sessions(platform: str = None):
    """List all cookie sessions"""
    try:
        sessions = auth_manager.list_sessions(platform)
        return {"sessions": sessions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list sessions: {e}")

@APP.delete("/api/auth/cookies/sessions/{platform}/{session_id}")
async def delete_cookie_session(platform: str, session_id: str):
    """Delete a cookie session"""
    try:
        result = auth_manager.delete_session(platform, session_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete session: {e}")

@APP.post("/api/auth/cookies/validate")
async def validate_cookies(platform: str, session_name: str = "default"):
    """Validate cookies for a platform"""
    try:
        result = auth_manager.validate_cookies(platform, session_name)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to validate cookies: {e}")

@APP.get("/api/auth/cookies/export/{platform}/{session_id}")
async def export_cookie_session(platform: str, session_id: str):
    """Export cookie session as downloadable file"""
    try:
        zip_path = auth_manager.export_session(platform, session_id)
        if not zip_path:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return FileResponse(
            zip_path,
            media_type="application/zip",
            filename=f"{platform}_{session_id}_cookies.zip"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to export session: {e}")

@APP.post("/api/auth/cookies/import/{platform}")
async def import_cookie_session(platform: str, file: bytes = Body(...)):
    """Import cookie session from uploaded file"""
    try:
        import tempfile
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as temp_file:
            temp_file.write(file)
            temp_path = temp_file.name
        
        try:
            result = auth_manager.import_session(platform, temp_path)
            return result
        finally:
            os.unlink(temp_path)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to import session: {e}")

@APP.post("/api/auth/cookies/cleanup")
async def cleanup_old_sessions(days: int = 30):
    """Clean up old cookie sessions"""
    try:
        cleaned = auth_manager.cleanup_old_sessions(days)
        return {
            "success": True,
            "cleaned_sessions": cleaned,
            "count": len(cleaned),
            "message": f"Cleaned {len(cleaned)} old sessions"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cleanup sessions: {e}")


# Photo download support for all platforms
try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    requests = None
    BeautifulSoup = None

def get_og_image(url: str) -> Optional[str]:
    """Extract photo/thumbnail from URL using OG tags or platform-specific logic"""
    if not requests or not BeautifulSoup:
        return None

    # Special handling for YouTube
    yt_match = re.search(r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{11})", url)
    if yt_match:
        vid = yt_match.group(1)
        return f"https://img.youtube.com/vi/{vid}/maxresdefault.jpg"

    # Special handling for other platforms if needed (e.g., Instagram, TikTok)
    platform = _infer_platform(url)
    if platform == 'instagram':
        # Instagram often has direct image URLs in OG tags
        pass  # Rely on OG tags below
    elif platform == 'tiktok':
        # TikTok thumbnails
        pass
    # Add more platform-specific logic as needed

    try:
        headers = {
            "User-Agent": os.environ.get('USER_AGENT', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'),
            "Accept-Language": os.environ.get('ACCEPT_LANGUAGE', 'en-US,en;q=0.9'),
            "Accept": "*/*"
        }
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")

        # Try og:image
        og_image = soup.find("meta", property="og:image")
        if og_image and og_image.get("content"):
            img_url = og_image["content"]
            # Validate if it's a valid image URL
            if img_url.startswith(('http://', 'https://')):
                return img_url

        # Fallback: twitter:image
        twitter_image = soup.find("meta", attrs={"name": "twitter:image"})
        if twitter_image and twitter_image.get("content"):
            img_url = twitter_image["content"]
            if img_url.startswith(('http://', 'https://')):
                return img_url

        # Fallback: first img tag with src
        first_img = soup.find("img", src=True)
        if first_img:
            img_src = first_img["src"]
            if img_src.startswith(('http://', 'https://')):
                return img_src
            else:
                # Make relative URLs absolute
                return urljoin(url, img_src)

    except Exception:
        pass

    return None

@APP.get("/get-photo")
async def get_photo(url: str = Query(..., description="URL to extract photo from")):
    """Extract and return photo/thumbnail URL from any supported platform"""
    try:
        image_url = get_og_image(url)
        if not image_url:
            return JSONResponse({"success": False, "error": "Image not found or unsupported platform"}, status_code=404)

        # Optional: Validate the image URL is accessible
        if httpx:
            try:
                async with httpx.AsyncClient(timeout=5) as client:
                    resp = await client.head(image_url)
                    if resp.status_code != 200:
                        return JSONResponse({"success": False, "error": "Image URL not accessible"}, status_code=404)
            except Exception:
                pass  # Skip validation if httpx fails

        return {"success": True, "image_url": image_url, "platform": _infer_platform(url)}
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)

# Default root redirects to the unified Tailwind frontend
@APP.get("/")
async def root_redirect():
    return RedirectResponse(url="/universal_tailwind", status_code=307)

# Run: uvicorn main_api:APP --host 0.0.0.0 --port 8000