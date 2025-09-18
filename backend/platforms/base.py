import os
import re
import shutil
import logging
import yt_dlp
from typing import Dict, Any, List, Tuple, Optional
import sys
from pathlib import Path

logger = logging.getLogger(__name__)
_REQUESTS_WARNED = False


def _validate_netscape_format(cookies_file):
    """Validate if cookies file is in Netscape format and catch common pitfalls.
    - Must be Netscape format (tabs/header)
    - For each cookie line, the include_subdomains flag must match the leading dot on domain
      (Python's http.cookiejar asserts this: domain startswith('.') <=> flag == TRUE)
    """
    try:
        with open(cookies_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        lines = content.splitlines()
        if not lines:
            return False, "Empty file"

        # Check for Netscape header
        has_header = any('# Netscape HTTP Cookie File' in line for line in lines[:5])

        # Check for tab-separated format
        tab_lines = [line for line in lines if line.strip() and not line.startswith('#')]
        has_tabs = any('\t' in line for line in tab_lines[:3])

        # Check for JSON format (invalid)
        is_json = content.lstrip().startswith('{')

        if is_json:
            return False, "JSON format detected - use Netscape format instead"

        if not has_tabs and not has_header:
            return False, "Not in Netscape format (missing tabs and header)"

        # Extra sanity: ensure domain flag matches leading dot to avoid http.cookiejar AssertionError
        for ln in tab_lines[:2000]:  # scan a reasonable amount of lines
            parts = ln.split('\t')
            if len(parts) < 2:
                # malformed content, but let yt-dlp decide; we only validate structure here
                continue
            domain = parts[0].strip()
            flag = parts[1].strip().upper()
            if domain.startswith('.'):
                if flag != 'TRUE':
                    return False, f"Domain flag mismatch for {domain}: expected TRUE with leading dot"
            else:
                if flag != 'FALSE':
                    return False, f"Domain flag mismatch for {domain}: expected FALSE without leading dot"

        return True, "Valid Netscape format"

    except Exception as e:
        return False, f"Error reading file: {e}"


def _safe_int(value, default):
    """Safely parse an int from env/user input. Returns default on any error."""
    try:
        if value is None:
            return default
        if isinstance(value, int):
            return value
        s = str(value).strip()
        # Handle empty string
        if not s:
            return default
        return int(s)
    except Exception:
        return default


def _safe_bool(value, default=False):
    """Parse a boolean-like value from env/user input.
    Accepts: '1', 'true', 'yes', 'on' (case-insensitive) for True; '0', 'false', 'no', 'off' for False.
    """
    try:
        if isinstance(value, bool):
            return value
        s = str(value).strip().lower()
        if s in ("1", "true", "yes", "on"):  # noqa: PLC1901
            return True
        if s in ("0", "false", "no", "off"):
            return False
        return default
    except Exception:
        return default

def build_ydl_opts(overrides=None, platform=None, progress_hooks: Optional[List] = None, cachedir: Optional[bool] = None):
    """Build minimal, fast yt-dlp options for optimal performance.
    - Safe env parsing prevents crashes on invalid env values
    - Optional progress_hooks for download/progress monitoring
    - cachedir toggle (default False) to avoid local caching unless explicitly enabled
    """
    # Defaults with safe parsing
    socket_timeout = _safe_int(os.environ.get('SOCKET_TIMEOUT'), 10)
    retries = _safe_int(os.environ.get('RETRIES'), 2)
    conc_frags = _safe_int(os.environ.get('MAX_CONCURRENT_FRAGMENTS'), 8)
    http_chunk = _safe_int(os.environ.get('HTTP_CHUNK_SIZE'), 10485760)
    fragment_retries = _safe_int(os.environ.get('FRAGMENT_RETRIES'), 3)
    user_agent = os.environ.get('USER_AGENT', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36')

    opts = {
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
        'ignore_no_formats_error': True,  # allow image-only posts (e.g., Instagram) to succeed
        'socket_timeout': socket_timeout,
        'retries': retries,
        'concurrent_fragment_downloads': conc_frags,
        'http_chunk_size': http_chunk,
        'user_agent': user_agent,
        # Performance optimizations
        'fragment_retries': fragment_retries,
        'skip_unavailable_fragments': True,
        'keep_fragments': False,
        'buffersize': 16384,
        # Disable cache unless explicitly enabled
        'cachedir': _safe_bool(os.environ.get('YTDLP_CACHEDIR', False) if cachedir is None else cachedir, False),
        'http_headers': {
            'User-Agent': user_agent,
            'Accept-Language': os.environ.get('ACCEPT_LANGUAGE', 'en-US,en;q=0.9'),
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive'
        }
    }

    # Default format sorting to favor progressive MP4 and quality unless overridden
    opts.setdefault('format_sort', ['hasaud', 'ext:mp4:m4a', 'res', 'fps', 'tbr', 'filesize'])
    opts.setdefault('format_sort_force', True)

    # Platform-specific tuning
    if platform:
        p = str(platform).lower()
        # Baseline fast-path defaults already set above
        # YouTube: keep fast (10-15s), playlists handled by caller via extract_flat
        if p in ('youtube', 'youtu', 'yt'):
            try:
                if (opts.get('socket_timeout') or 0) > 15:
                    opts['socket_timeout'] = 15
            except Exception:
                opts['socket_timeout'] = 15
            # keep retries low for speed
            try:
                if (opts.get('retries') or 0) > 2:
                    opts['retries'] = 2
            except Exception:
                opts['retries'] = 2
        # Flaky/slow platforms: allow 25–30s and a few retries
        elif p in ('instagram', 'facebook', 'tiktok', 'twitter', 'x', 'pinterest', 'linkedin', 'reddit', 'snapchat'):
            try:
                if (opts.get('socket_timeout') or 0) < 25:
                    opts['socket_timeout'] = 25
            except Exception:
                opts['socket_timeout'] = 25
            try:
                if (opts.get('retries') or 0) < 3:
                    opts['retries'] = 3
            except Exception:
                opts['retries'] = 3
            try:
                if (opts.get('fragment_retries') or 0) < 4:
                    opts['fragment_retries'] = 4
            except Exception:
                opts['fragment_retries'] = 4
        # Generic/others: modest bump
        else:
            try:
                if (opts.get('socket_timeout') or 0) < 20:
                    opts['socket_timeout'] = 20
            except Exception:
                opts['socket_timeout'] = 20
    # Proxy support and IPv4 preference
    proxy_url = None
    proxy_source = None
    try:
        if isinstance(overrides, dict) and overrides.get('proxy'):
            proxy_url = overrides.get('proxy')
            proxy_source = 'override'
    except Exception:
        proxy_url = None
    if not proxy_url:
        env_proxy = os.environ.get('PROXY_URL') or os.environ.get('ALL_PROXY') or os.environ.get('HTTPS_PROXY') or os.environ.get('HTTP_PROXY')
        if env_proxy:
            proxy_url = env_proxy
            proxy_source = 'env'
    if proxy_url:
        opts['proxy'] = proxy_url
        try:
            logger.debug(f"Using proxy from {proxy_source}: {proxy_url}")
        except Exception:
            pass
    if _safe_bool(os.environ.get('YTDLP_PREFER_IPV4') or os.environ.get('FORCE_IPV4'), False):
        opts['prefer_ipv4'] = True

    # Optional progress hooks
    if progress_hooks:
        try:
            opts['progress_hooks'] = list(progress_hooks)
        except Exception:
            # Be resilient if caller passes non-iterable
            opts['progress_hooks'] = [progress_hooks]  # type: ignore

    ffmpeg_loc = os.environ.get('FFMPEG_LOCATION') or os.environ.get('FFMPEG_PATH')
    if ffmpeg_loc and (os.path.isabs(ffmpeg_loc) and (os.path.isdir(ffmpeg_loc) or os.path.isfile(ffmpeg_loc))):
        opts['ffmpeg_location'] = ffmpeg_loc

    # Cookies from browser (preferred)
    cookies_from_browser = os.environ.get('YTDLP_COOKIES_FROM_BROWSER')
    if cookies_from_browser:
        browser_name = cookies_from_browser.strip().lower()
        opts['cookiesfrombrowser'] = (browser_name,)
    
    # Try to get cookies from auth manager first, then fallback to environment
    cookies_file = None
    if platform:
        try:
            from backend.auth_manager import auth_manager
            cookies_file = auth_manager.get_cookies_file(platform)
        except Exception:
            pass
    
    # Fallback to environment variable
    if not cookies_file:
        cookies_file = os.environ.get('COOKIES_FILE')
    
    if cookies_file and os.path.exists(cookies_file):
        # Validate Netscape format using proper validation logic
        try:
            valid, message = _validate_netscape_format(cookies_file)
            if valid:
                opts['cookiefile'] = cookies_file
                logger.debug(f"Using valid cookies file: {cookies_file} ({message})")
            else:
                # Skip invalid cookies file instead of crashing
                # Optional: honor STRICT_COOKIES to force usage
                if _safe_bool(os.environ.get('STRICT_COOKIES'), False):
                    opts['cookiefile'] = cookies_file  # let yt-dlp decide; may error
                    logger.warning(f"Forced usage of invalid cookies file: {cookies_file} ({message})")
                else:
                    logger.warning(f"Invalid cookies file format detected; skipping cookiefile: {message}. Set STRICT_COOKIES=1 to force usage.")
        except Exception as _e:
            # Log once for visibility, but continue
            try:
                logger.warning(f"Failed to read/validate cookies file: {cookies_file}: {_e}")
            except Exception:
                pass

    try:
        aria2c_path = os.environ.get('ARIA2C_PATH') or shutil.which('aria2c')
        if aria2c_path:
            opts['external_downloader'] = 'aria2c'
            threads = max(1, min(16, _safe_int(os.environ.get('ARIA2C_THREADS'), 16)))
            max_connections = max(1, min(16, _safe_int(os.environ.get('ARIA2C_MAX_CONNECTIONS'), 16)))
            opts['external_downloader_args'] = [
                f'--max-connection-per-server={max_connections}',
                f'--split={threads}',
                '--min-split-size=1M',
                '--max-download-limit=0',
                '--enable-http-pipelining=true',
                '--file-allocation=none',
                '--console-log-level=warn',
                '--summary-interval=0',
                '--download-result=hide',
                '--disable-ipv6=false',
                '--optimize-concurrent-downloads=true',
                '--max-tries=3',
                '--retry-wait=1',
                '--timeout=10',
                '--connect-timeout=10'
            ]
    except Exception:
        pass

    if overrides:
        opts.update(overrides)
    return opts

def _build_image_formats(info: Dict[str, Any]) -> List[Dict[str, Any]]:
    images = []
    # For Instagram, images are in display_resources
    if "display_resources" in info:
        for idx, img in enumerate(info["display_resources"]):
            images.append({
                "format_id": f"img{idx}",
                "ext": "jpg",
                "width": img.get("config_width"),
                "height": img.get("config_height"),
                "url": img.get("src"),
                "filesize": None,
                "type": "image",
                "quality": f"{img.get('config_height')}p",
            })
    # For other platforms, they might be in thumbnails or a direct url
    elif "thumbnails" in info:
        for thumb in info["thumbnails"]:
            images.append({
                "format_id": thumb.get('id', 'img'),
                "ext": thumb.get('ext', 'jpg'),
                "width": thumb.get('width'),
                "height": thumb.get('height'),
                "url": thumb.get('url'),
                "filesize": None,
                "type": "image",
                "quality": f"{thumb.get('height')}p",
            })
    elif "url" in info:
        images.append({
            "format_id": "img0",
            "ext": info.get('ext', 'jpg'),
            "width": info.get('width'),
            "height": info.get('height'),
            "url": info["url"],
            "filesize": None,
            "type": "image",
            "quality": f"{info.get('height')}p",
        })
    return images

def get_best_thumbnail(item: Dict[str, Any]) -> Optional[str]:
    """Choose best thumbnail with robust fallbacks (Instagram-friendly).
    Also validates URL with a quick HEAD/GET check to avoid hotlink-blocked images.
    Returns a guaranteed-safe placeholder when blocked or missing.
    """

    def _url_ok(u: Optional[str]) -> bool:
        if not u or not isinstance(u, str):
            return False
        u = u.strip()
        if not (u.startswith('http://') or u.startswith('https://')):
            return False
        try:
            # Import locally to avoid global dependency if unused on some platforms
            import requests  # type: ignore
            headers = {
                'User-Agent': os.environ.get('USER_AGENT', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'),
                'Accept': '*/*',
                'Accept-Language': os.environ.get('ACCEPT_LANGUAGE', 'en-US,en;q=0.9')
            }
            # Try HEAD first
            r = requests.head(u, headers=headers, allow_redirects=True, timeout=5)
            if r.status_code == 200:
                return True
            # Some CDNs block HEAD (405) or require a small GET; attempt minimal GET
            rng_headers = dict(headers)
            rng_headers['Range'] = 'bytes=0-0'
            g = requests.get(u, headers=rng_headers, stream=True, allow_redirects=True, timeout=7)
            try:
                if g.status_code in (200, 206):
                    return True
            finally:
                try:
                    g.close()
                except Exception:
                    pass
        except Exception:
            return False
        return False

    thumb_url = (
        item.get('thumbnail')
        or item.get('thumbnail_url')
        or item.get('display_url')
    )
    if not thumb_url:
        thumbs = item.get('thumbnails') or []
        if isinstance(thumbs, list) and thumbs:
            try:
                best = max(thumbs, key=lambda t: ((t.get('height') or 0), (t.get('width') or 0)))
                thumb_url = best.get('url') or best.get('src')
            except Exception:
                thumb_url = thumbs[0].get('url') or thumbs[0].get('src')
    if not thumb_url:
        dr = item.get('display_resources') or []
        if isinstance(dr, list) and dr:
            try:
                best = max(dr, key=lambda r: ((r.get('config_height') or 0), (r.get('config_width') or 0)))
                thumb_url = best.get('src')
            except Exception:
                thumb_url = dr[-1].get('src')

    # Validate and fallback to a safe placeholder when blocked/missing
    # Allow skipping validation via env flag for speed or offline usage
    if os.environ.get('SKIP_THUMBNAIL_VALIDATION', '').strip().lower() in ('1', 'true', 'yes', 'on'):
        return thumb_url or os.environ.get('DEFAULT_THUMBNAIL', '/static/og-default.svg')

    if _url_ok(thumb_url):
        return thumb_url
    # If requests is not installed or validation fails, log once and use default placeholder
    global _REQUESTS_WARNED
    if not _REQUESTS_WARNED:
        try:
            import importlib.util
            if importlib.util.find_spec('requests') is None:
                logger.warning("requests not installed; thumbnail validation disabled. Using DEFAULT_THUMBNAIL or fallback.")
        except Exception:
            pass
        _REQUESTS_WARNED = True
    return os.environ.get('DEFAULT_THUMBNAIL', '/static/og-default.svg')

def analyze_platform(url: str, platform_name: str, url_patterns: List[re.Pattern]) -> Dict[str, Any]:
    """Generic function to analyze a URL from a supported platform."""
    # When url_patterns is empty or None, skip pattern validation (used by image direct re-analysis)
    if url_patterns:
        if not any(p.search(url or "") for p in url_patterns):
            raise ValueError(f"Invalid {platform_name.capitalize()} URL")

    ydl_opts = build_ydl_opts({
        'skip_download': True,
        'http_headers': {
            'Referer': f'https://www.{platform_name.lower()}.com/',
            'User-Agent': os.environ.get('USER_AGENT', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'),
            'Accept-Language': os.environ.get('ACCEPT_LANGUAGE', 'en-US,en;q=0.9')
        }
    }, platform=platform_name)

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
        except Exception as e:
            # Retry with flat extraction for resilience (works for many sites to at least fetch metadata)
            try:
                fallback_opts = dict(ydl_opts)
                fallback_opts['extract_flat'] = 'discard_in_playlist'
                with yt_dlp.YoutubeDL(fallback_opts) as ydl2:
                    info = ydl2.extract_info(url, download=False)
            except Exception:
                raise e

    if not info:
        raise ConnectionError(f"Failed to analyze {platform_name.capitalize()} URL")

    entries = info.get('entries', [info]) if info.get('_type') == 'playlist' else [info]

    normalized_items = []
    for item in entries:
        # Robust media type detection: prefer real MP4 video formats; otherwise treat as image
        fmts = item.get('formats') or []
        has_video_mp4 = False
        for _f in fmts:
            try:
                _ext = (_f.get('ext') or 'mp4').lower()
                _h = _f.get('height') or 0
                _w = _f.get('width') or 0
                if _ext == 'mp4' and (_h > 0 or _w > 0):
                    has_video_mp4 = True
                    break
            except Exception:
                continue
        is_image_ext = (item.get('ext') or '').lower() in ('jpg', 'jpeg', 'png', 'webp')
        is_video = True if has_video_mp4 else False
        
        video_formats = []
        audio_formats = []
        image_formats = []

        if is_video:
            seen = set()
            for f in fmts:
                height = f.get('height') or 0
                width = f.get('width') or 0
                ext = (f.get('ext') or 'mp4').lower()
                if (height <= 0 and width <= 0) or ext != 'mp4':
                    continue
                
                fps = f.get('fps') or 0
                tbr = f.get('tbr') or 0
                key = (height, fps, ext, tbr)
                if key in seen:
                    continue
                seen.add(key)

                filesize = f.get('filesize') or f.get('filesize_approx')
                estimated = None
                if not filesize:
                    try:
                        # Estimate size from tbr (Kbps) and duration (s): bytes = duration * tbr*1000 / 8
                        dur = item.get('duration') or 0
                        if dur and tbr:
                            estimated = int((dur * tbr * 1000) / 8)
                    except Exception:
                        estimated = None
                size_str = (
                    f"{round(filesize / 1048576, 1):.1f} MB" if filesize else (
                        f"≈ {round(estimated / 1048576, 1):.1f} MB" if estimated else 'Unknown size'
                    )
                )
                video_formats.append({
                    'format_id': f.get('format_id'),
                    'ext': ext.upper(),
                    'quality': f"{height}p" if height else 'Video',
                    'resolution': f"{width}x{height}" if height else None,
                    'height': height,
                    'fps': fps,
                    'size': size_str,
                    'filesize_mb': round(filesize / 1048576, 1) if filesize else None,
                    'estimated_size_mb': round(estimated / 1048576, 1) if (not filesize and estimated) else None,
                    'url': f.get('url'),
                    'has_direct_url': bool(f.get('url')),
                    'is_progressive': f.get('vcodec') != 'none' and f.get('acodec') != 'none',
                    'vcodec': f.get('vcodec'),
                    'acodec': f.get('acodec'),
                    'tbr': tbr,
                    'type': 'video'
                })
            # Build instant audio options (audio-only direct URLs)
            for f in fmts:
                try:
                    vcodec = (f.get('vcodec') or 'none').lower()
                    acodec = (f.get('acodec') or 'none').lower()
                    ext_a = (f.get('ext') or '').lower()
                    is_audio_only = (vcodec == 'none' and acodec != 'none') or ext_a in ('m4a', 'webm', 'mp3')
                    if not is_audio_only:
                        continue
                    abr = f.get('abr') or f.get('tbr') or 0
                    filesize = f.get('filesize') or f.get('filesize_approx')
                    size_str = f"{round(filesize / 1048576, 1):.1f} MB" if filesize else 'Unknown size'
                    audio_formats.append({
                        'format_id': f.get('format_id'),
                        'ext': (f.get('ext') or '').upper(),
                        'quality': f"Instant Audio {int(abr)} kbps" if abr else 'Instant Audio',
                        'size': size_str,
                        'filesize_mb': round(filesize / 1048576, 1) if filesize else None,
                        'has_direct_url': bool(f.get('url')),
                        'url': f.get('url'),
                        'type': 'audio'
                    })
                except Exception:
                    continue
        else:
            image_formats = _build_image_formats(item)

        # Choose best thumbnail with robust fallbacks (important for Instagram)
        thumb_url = get_best_thumbnail(item)

        normalized_items.append({
            'id': item.get('id'),
            'title': item.get('title') or item.get('id') or f"{platform_name.capitalize()} Media",
            'thumbnail': thumb_url,
            'duration': item.get('duration'),
            'uploader': item.get('uploader') or item.get('channel') or 'Unknown',
            'formats': video_formats + image_formats, # Combine all formats
            'media_type': 'video' if is_video else 'image'
        })

    if not normalized_items:
        raise ValueError("No media found")

    first_item = normalized_items[0]
    
    # Extract all image formats for consistent frontend consumption
    all_images = []
    for item in normalized_items:
        all_images.extend([f for f in item['formats'] if f['type'] == 'image'])
    
    # Determine if instant download is available (progressive MP4) for Facebook
    instant_available = False
    if (platform_name or '').lower() == 'facebook':
        for _item in normalized_items:
            for _f in _item.get('formats', []):
                if (
                    _f.get('type') == 'video'
                    and (_f.get('ext') or '').upper() == 'MP4'
                    and _f.get('is_progressive')
                ):
                    instant_available = True
                    break
            if instant_available:
                break

    return {
        'title': first_item['title'],
        'thumbnail': first_item['thumbnail'],
        'duration': first_item['duration'],
        'uploader': first_item['uploader'],
        'media_type': first_item['media_type'],
        'mp4': [f for f in first_item['formats'] if f['type'] == 'video'],
        'mp3': [f for f in first_item['formats'] if f['type'] == 'audio'],  # Instant audio (direct URLs)
        'jpg': [f for f in first_item['formats'] if f['type'] == 'image'],
        'images': all_images,  # Consistent field name for frontend
        'items': normalized_items,
        'count': len(normalized_items),
        'instant_available': instant_available
    }

def prepare_download_options(url: str, format_id: str, platform_name: str, info: Optional[Dict[str, Any]] = None) -> Tuple[Dict[str, Any], str]:
    """
    Prepares download options for a video or image.
    - Images: returns direct URL for instant download
    - Audio-only (MP3/M4A/Best): provide instant audio extraction or bestaudio without transcoding
    - Facebook: tries instant MP4 with audio via helper; falls back to yt-dlp merge
    - Others: prefer instant progressive MP4 (direct URL) when available, else normal yt-dlp with bestaudio merge
    """
    base_downloads = os.path.abspath(os.getenv("DOWNLOAD_FOLDER", os.path.join(os.getcwd(), "downloads")))
    outdir = os.path.join(base_downloads, platform_name.lower())
    os.makedirs(outdir, exist_ok=True)

    # IMAGE HANDLING (direct)
    if str(format_id).startswith('img'):
        if info is None:
            # Skip URL pattern validation for re-analysis
            info = analyze_platform(url, platform_name, [])
        img_url = None
        for item in (info.get('items', []) if isinstance(info, dict) else []):
            for f in item.get('formats', []):
                if str(f.get('format_id')) == str(format_id):
                    img_url = f.get('url')
                    break
            if img_url:
                break
        if not img_url:
            raise ValueError("Image format not found")
        return {'direct_url': img_url}, outdir

    # INSTANT AUDIO HANDLING (direct)
    if format_id and '+' not in str(format_id):
        if info is None:
            analyzed = analyze_platform(url, platform_name, [])
        else:
            analyzed = info
        # Check top-level instant audio list
        if isinstance(analyzed, dict):
            for a in (analyzed.get('mp3') or []):
                if str(a.get('format_id')) == str(format_id) and a.get('has_direct_url') and a.get('url'):
                    return {'direct_url': a['url']}, outdir
        # Check per-item formats for audio
        for item in (analyzed.get('items', []) if isinstance(analyzed, dict) else []):
            for f in item.get('formats', []):
                if str(f.get('format_id')) == str(format_id) and f.get('type') == 'audio' and f.get('url'):
                    return {'direct_url': f['url']}, outdir

    # AUDIO-ONLY HANDLING (MP3/M4A/BEST PASSTHROUGH)
    fid = (format_id or '').lower()
    if fid in {'audio', 'bestaudio', 'audio_best'}:
        # No transcoding: keep original best audio container
        ydl_opts = build_ydl_opts({
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(outdir, '%(uploader|sanitize)s - %(title|sanitize)s [%(id)s].%(ext)s'),
            'http_headers': {
                'Referer': f'https://www.{platform_name.lower()}.com/'
            }
        })
        return ydl_opts, outdir
    if fid in {'mp3', 'audio_mp3'} or re.match(r'(?i)^mp3[_-]?(\d{2,3})$', fid or ''):
        # Support mp3_128 style with clamped bitrate
        m = re.match(r'(?i)^mp3[_-]?(\d{2,3})$', fid or '')
        bitrate = int(m.group(1)) if m else 192
        clamped = max(32, min(320, bitrate))
        if clamped != bitrate:
            try:
                logger = logging.getLogger(__name__)
                logger.warning(f"mp3 bitrate {bitrate} out of range; clamped to {clamped}")
            except Exception:
                pass
        ydl_opts = build_ydl_opts({
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(outdir, '%(uploader|sanitize)s - %(title|sanitize)s [%(id)s].%(ext)s'),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': str(clamped),
            }],
            'http_headers': {
                'Referer': f'https://www.{platform_name.lower()}.com/'
            }
        })
        return ydl_opts, outdir
    if fid in {'m4a', 'audio_m4a'}:
        # Prefer native m4a when available; otherwise extract to m4a
        ydl_opts = build_ydl_opts({
            'format': 'bestaudio[ext=m4a]/bestaudio/best',
            'outtmpl': os.path.join(outdir, '%(uploader|sanitize)s - %(title|sanitize)s [%(id)s].%(ext)s'),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'm4a',
                'preferredquality': '192',
            }],
            'http_headers': {
                'Referer': f'https://www.{platform_name.lower()}.com/'
            }
        })
        return ydl_opts, outdir

    # FACEBOOK VIDEO INSTANT DOWNLOAD (audio+video when available)
    if platform_name.lower() == "facebook":
        try:
            from .facebook_helper import get_facebook_mp4  # Optional helper for instant URLs
            mp4_url = get_facebook_mp4(url)
            if mp4_url:
                return {'direct_url': mp4_url}, outdir
        except Exception:
            # Fallback to yt-dlp below
            pass

    # GENERIC INSTANT PROGRESSIVE MP4 (direct URL) WHEN AVAILABLE
    try:
        if format_id and format_id not in {'best'} and '+' not in str(format_id):
            if info is None:
                # Quick re-analysis to locate the chosen format and check direct URL
                analyzed = analyze_platform(url, platform_name, [])
            else:
                analyzed = info
            # Top-level mp4 list contains formats for the first item
            mp4_list = (analyzed.get('mp4') or []) if isinstance(analyzed, dict) else []
            selected = next((f for f in mp4_list if str(f.get('format_id')) == str(format_id)), None)
            if selected and selected.get('is_progressive') and selected.get('has_direct_url') and selected.get('url'):
                return {'direct_url': selected['url']}, outdir
    except Exception:
        # Ignore and continue with normal yt-dlp flow
        pass

    # NORMAL yt-dlp VIDEO (merge bestaudio with selected video)
    format_selector = f"{format_id}+bestaudio/{format_id}" if format_id and '+' not in str(format_id) else str(format_id)
    ydl_opts = build_ydl_opts({
        'format': format_selector,
        'outtmpl': os.path.join(outdir, '%(uploader|sanitize)s - %(title|sanitize)s [%(id)s].%(ext)s'),
        'merge_output_format': 'mp4',
        'http_headers': {
            'Referer': f'https://www.{platform_name.lower()}.com/'
        }
    })
    return ydl_opts, outdir
