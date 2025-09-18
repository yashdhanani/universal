import re
import logging
import time
import os
from urllib.parse import urlparse, parse_qs
from .base import analyze_platform, prepare_download_options, build_ydl_opts, get_best_thumbnail
try:
    import httpx  # type: ignore
except Exception:  # httpx is optional; URL resolution will skip if missing
    httpx = None  # type: ignore

logger = logging.getLogger(__name__)

PLATFORM_NAME = "facebook"
# Permissive but focused matching to include nested paths and optional queries
URL_PATTERNS = [
    # Common media/permalink endpoints anywhere in the path, query optional
    re.compile(r"https?://(www\.)?facebook\.com/.*(photo\.php|permalink\.php|video\.php|watch|/posts/|/photos/|/videos/|/reel/|/reels/).*", re.I),
    # Short and watch domains
    re.compile(r"https?://fb\.watch/.*", re.I),
    re.compile(r"https?://fb\.me/.*", re.I),
]

# Short TTL cache for fb.me redirect resolution to avoid repeated network calls
_FBME_CACHE_TTL = 30  # seconds
_fbme_cache = {}  # type: ignore[var-annotated]


def _normalize_facebook_url(url: str) -> str:
    """Clean Facebook URLs, resolve short links, and reconstruct canonical video URLs.
    - fb.watch links are returned as-is
    - fb.me links are resolved via HEAD/GET (short TTL cache)
    - facebook.com links: try to extract a numeric video ID from the path or query and
      normalize to https://www.facebook.com/watch/?v=<id>, else strip tracking params.
    """
    try:
        parsed = urlparse(url)
        netloc = (parsed.netloc or '').lower()

        # fb.watch: keep original
        if 'fb.watch' in netloc:
            return url

        # fb.me: try to resolve redirect (optional, best-effort) with short TTL cache
        if 'fb.me' in netloc:
            now = time.time()
            cached = _fbme_cache.get(url)
            if cached:
                resolved, ts = cached
                if (now - ts) < _FBME_CACHE_TTL and resolved:
                    return resolved
            if httpx is not None:
                try:
                    resp = httpx.head(url, follow_redirects=True, timeout=5)
                    if resp is not None and str(resp.url):
                        resolved = str(resp.url)
                        _fbme_cache[url] = (resolved, now)
                        return resolved
                except Exception as e:
                    logger.debug("fb.me HEAD resolve failed for '%s': %s", url, e)
                # Fallback: attempt GET with redirects (some servers block HEAD)
                try:
                    resp = httpx.get(url, follow_redirects=True, timeout=5)
                    if resp is not None and str(resp.url):
                        resolved = str(resp.url)
                        _fbme_cache[url] = (resolved, now)
                        return resolved
                except Exception as e:
                    logger.debug("fb.me GET resolve failed for '%s': %s", url, e)
            # If httpx missing or both fail, return original
            return url

        # facebook.com: attempt to canonicalize video links
        if 'facebook.com' in netloc:
            from urllib.parse import urlencode, urlunparse
            path = parsed.path or ''
            path_lower = path.lower()
            query_params = parse_qs(parsed.query)

            # 1) Prefer explicit video id in query (?v=...)
            vid = None
            v_vals = query_params.get('v') or []
            if v_vals:
                vid = v_vals[0]

            # 2) Try to extract numeric id from common path patterns
            if not vid:
                # /videos/<id>/ or /videos/<slug>/<id>/
                m = re.search(r"/videos/(?:[^/]+/)?(?P<id>\d{8,})(?:/|$)", path_lower)
                if m:
                    vid = m.group('id')

            if not vid:
                # Trailing numeric segment anywhere in path (fallback)
                m2 = re.search(r"/(?P<id>\d{8,})(?:/|$)", path_lower)
                if m2:
                    vid = m2.group('id')

            # If we found a plausible video id:
            if vid:
                if 'video.php' in path_lower:
                    # Keep video.php with cleaned params (tests expect this)
                    keep_params = ['v', 'id']
                    from urllib.parse import urlencode, urlunparse
                    clean_params = {k: query_params[k] for k in keep_params if k in query_params}
                    ordered_items = [(k, clean_params[k]) for k in ['v', 'id'] if k in clean_params]
                    clean_query = urlencode(ordered_items, doseq=True) if ordered_items else ''
                    return urlunparse((parsed.scheme, parsed.netloc, path, parsed.params, clean_query, ''))
                else:
                    # For non-video.php paths, normalize to watch URL
                    return f"https://www.facebook.com/watch/?v={vid}"

            # 3) Otherwise, remove tracking while keeping essentials for known endpoints
            keep_params = ['story_fbid', 'id', 'set', 'type', 'fbid', 'v']
            clean_params = {k: query_params[k] for k in keep_params if k in query_params}

            # Order params per endpoint for deterministic tests
            if 'permalink.php' in path_lower:
                order_keys = ['story_fbid', 'id']
            elif 'photo.php' in path_lower:
                order_keys = ['fbid', 'set', 'type']
            elif 'video.php' in path_lower:
                order_keys = ['v', 'id']
            else:
                order_keys = sorted(clean_params.keys())

            ordered_items = [(k, clean_params[k]) for k in order_keys if k in clean_params]
            clean_query = urlencode(ordered_items, doseq=True) if ordered_items else ''
            return urlunparse((parsed.scheme, parsed.netloc, path, parsed.params, clean_query, ''))

    except Exception as e:
        logger.warning("Failed to normalize Facebook URL '%s': %s", url, e)

    return url


def _build_direct_fmt(url: str) -> dict:
    """Build a standardized progressive MP4 format entry for direct URLs."""
    return {
        'format_id': 'direct-mp4',
        'ext': 'MP4',
        'quality': 'Video',
        'resolution': None,
        'height': None,
        'fps': None,
        'size': 'Unknown size',
        'filesize_mb': None,
        'url': url,
        'has_direct_url': True,
        'is_progressive': True,
        'vcodec': None,
        'acodec': None,
        'tbr': None,
        'type': 'video',
        'source': 'direct'
    }


def analyze(url: str):
    """Analyze Facebook URL for videos and photos.

    Facebook posts can contain:
    - Single videos
    - Single photos
    - Photo albums/carousels
    - Mixed media posts

    If yt-dlp fails to parse (extractor breakages), fall back to a direct
    progressive MP4 URL when available, so users can still download.
    """
    normalized = _normalize_facebook_url(url)

    # Fast-path: optionally force instant fallback first to avoid extractor failures/noise
    if os.environ.get('FACEBOOK_FORCE_FALLBACK', '').strip() in ('1', 'true', 'True', 'YES', 'yes', 'on'):
        try:
            from .facebook_helper import get_facebook_mp4
            mp4_url = get_facebook_mp4(normalized)
            if mp4_url:
                vid = None
                m = re.search(r"[?&]v=(?P<id>\d{8,})", normalized)
                if not m:
                    m = re.search(r"/(?P<id>\d{8,})(?:/|$)", normalized)
                if m:
                    vid = m.group('id')

                fmt = _build_direct_fmt(mp4_url)
                item = {
                    'id': vid or 'facebook-video',
                    'title': 'Facebook Video',
                    'thumbnail': None,
                    'duration': None,
                    'uploader': 'Facebook',
                    'formats': [fmt],
                    'media_type': 'video'
                }
                return {
                    'title': item['title'],
                    'thumbnail': item['thumbnail'],
                    'duration': item['duration'],
                    'uploader': item['uploader'],
                    'media_type': item['media_type'],
                    'mp4': [fmt],
                    'mp3': [],
                    'jpg': [],
                    'images': [],
                    'items': [item],
                    'count': 1,
                    'instant_available': True
                }
        except Exception:
            # If forced path fails, proceed with regular analyze flow
            pass

    try:
        result = analyze_platform(normalized, PLATFORM_NAME, URL_PATTERNS)

        # Tag source for existing formats to help debugging
        for f in result.get('mp4', []) or []:
            if 'source' not in f:
                f['source'] = 'yt-dlp'

        # Only fallback when no progressive MP4 is present
        needs_video_fallback = not any(f.get('is_progressive') for f in (result.get('mp4') or []))
        try:
            if needs_video_fallback:
                from .facebook_helper import get_facebook_mp4
                mp4_url = get_facebook_mp4(normalized)
                if mp4_url:
                    # Extract an ID for display if possible
                    vid = None
                    m = re.search(r"[?&]v=(?P<id>\d{8,})", normalized)
                    if not m:
                        m = re.search(r"/(?P<id>\d{8,})(?:/|$)", normalized)
                    if m:
                        vid = m.group('id')

                    # Try to get better metadata (title/thumbnail/formats) via yt-dlp quick probe
                    info_title = None
                    info_thumb = result.get('thumbnail')
                    mp4_formats = []
                    try:
                        import yt_dlp
                        ydl_opts = build_ydl_opts({'skip_download': True, 'quiet': True}, platform='facebook')
                        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                            info = ydl.extract_info(normalized, download=False)
                        if info and info.get('_type') == 'playlist':
                            entries = info.get('entries') or []
                            if entries:
                                info = entries[0]
                        if info:
                            info_title = info.get('title') or info.get('id')
                            # Reuse robust thumbnail selection from base
                            info_thumb = info_thumb or get_best_thumbnail(info) or info.get('thumbnail')
                            for f in (info.get('formats') or []):
                                try:
                                    ext = (f.get('ext') or '').lower()
                                    if ext != 'mp4':
                                        continue
                                    height = f.get('height') or 0
                                    width = f.get('width') or 0
                                    if (height <= 0 and width <= 0):
                                        continue
                                    is_prog = f.get('vcodec') != 'none' and f.get('acodec') != 'none'
                                    filesize = f.get('filesize') or f.get('filesize_approx')
                                    mp4_formats.append({
                                        'format_id': f.get('format_id'),
                                        'ext': 'MP4',
                                        'quality': f"{height}p" if height else 'Video',
                                        'resolution': f"{width}x{height}" if height else None,
                                        'height': height,
                                        'fps': f.get('fps'),
                                        'size': f"{round(filesize / 1048576, 1):.1f} MB" if filesize else 'Unknown size',
                                        'filesize_mb': round(filesize / 1048576, 1) if filesize else None,
                                        'url': f.get('url'),
                                        'has_direct_url': bool(f.get('url')),
                                        'is_progressive': is_prog,
                                        'vcodec': f.get('vcodec'),
                                        'acodec': f.get('acodec'),
                                        'tbr': f.get('tbr'),
                                        'type': 'video',
                                        'source': 'yt-dlp'
                                    })
                                except Exception:
                                    continue
                    except Exception:
                        pass

                    # Always include the direct-mp4 as a fallback option
                    fmt = _build_direct_fmt(mp4_url)

                    item = {
                        'id': vid or 'facebook-video',
                        'title': info_title or 'Facebook Video',
                        'thumbnail': info_thumb,
                        'duration': None,
                        'uploader': 'Facebook',
                        'formats': (mp4_formats or []) + [fmt],
                        'media_type': 'video'
                    }
                    # Build a result consistent with frontend expectations
                    return {
                        'title': item['title'],
                        'thumbnail': item['thumbnail'],
                        'duration': item['duration'],
                        'uploader': item['uploader'],
                        'media_type': item['media_type'],
                        'mp4': [f for f in item['formats'] if f['type'] == 'video'],
                        'mp3': [],
                        'jpg': result.get('jpg') or [],
                        'images': result.get('images') or [],
                        'items': [item],
                        'count': 1,
                        'instant_available': True
                    }
        except Exception:
            # Fallback best-effort should never break primary result
            pass
        return result
    except Exception as e:
        logger.warning("yt-dlp analyze failed for Facebook, attempting instant fallback: %s", e)
        # Fallback: try direct progressive MP4 URL
        try:
            from .facebook_helper import get_facebook_mp4
            mp4_url = get_facebook_mp4(normalized)
            if not mp4_url:
                raise ValueError("No direct MP4 URL")

            # Extract an ID for display if possible
            vid = None
            m = re.search(r"[?&]v=(?P<id>\d{8,})", normalized)
            if not m:
                m = re.search(r"/(?P<id>\d{8,})(?:/|$)", normalized)
            if m:
                vid = m.group('id')

            # Minimal normalized structure compatible with frontend expectations
            fmt = _build_direct_fmt(mp4_url)
            item = {
                'id': vid or 'facebook-video',
                'title': 'Facebook Video',
                'thumbnail': None,
                'duration': None,
                'uploader': 'Facebook',
                'formats': [fmt],
                'media_type': 'video'
            }
            result = {
                'title': item['title'],
                'thumbnail': item['thumbnail'],
                'duration': item['duration'],
                'uploader': item['uploader'],
                'media_type': item['media_type'],
                'mp4': [fmt],
                'mp3': [],
                'jpg': [],
                'images': [],
                'items': [item],
                'count': 1,
                'instant_available': True
            }
            return result
        except Exception as e2:
            logger.error("Facebook instant fallback failed: %s", e2)
            raise


def prepare_download(url: str, format_id: str):
    normalized = _normalize_facebook_url(url)
    # Validate URL matches expected media patterns to avoid unexpected work
    if not any(p.search(normalized or "") for p in URL_PATTERNS):
        raise ValueError("Invalid Facebook URL")
    return prepare_download_options(normalized, format_id, PLATFORM_NAME)
