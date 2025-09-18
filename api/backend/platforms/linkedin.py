import re
from urllib.parse import urlparse, parse_qs
from .base import analyze_platform, prepare_download_options

PLATFORM_NAME = "linkedin"
# Stricter matching: posts and feed update permalinks
URL_PATTERNS = [
    # Article and post permalinks
    re.compile(r"https?://(www\.)?linkedin\.com/posts/[^/]+", re.I),
    # Feed update permalinks (activity)
    re.compile(r"https?://(www\.)?linkedin\.com/feed/update/urn:li:activity:\d+", re.I),
    # UGC post permalinks
    re.compile(r"https?://(www\.)?linkedin\.com/.*/ugcPost-\d+", re.I),
]


def _normalize_linkedin_url(url: str) -> str:
    """Clean LinkedIn URLs for better extraction.
    LinkedIn posts can have tracking parameters and various formats.
    """
    try:
        parsed = urlparse(url)
        
        # For linkedin.com URLs, clean tracking params
        if 'linkedin.com' in parsed.netloc:
            # Remove tracking parameters but keep essential ones
            query_params = parse_qs(parsed.query)
            clean_params = {}
            
            # Keep essential params for post identification
            keep_params = ['trk', 'originalSubdomain']  # Sometimes needed for access
            # Normalize some known post forms to canonical feed/update when possible
            path = parsed.path.rstrip('/')
            # Transform /posts/.../ugcPost-<id> to feed/update/urn:li:activity:<id> when detectable
            m = re.search(r"ugcPost-(\d+)", path)
            if m:
                # Keep host; build canonical feed URL
                new_path = f"/feed/update/urn:li:activity:{m.group(1)}"
                from urllib.parse import urlunparse
                return urlunparse((parsed.scheme, parsed.netloc, new_path, parsed.params, '', ''))
            for param in keep_params:
                if param in query_params:
                    clean_params[param] = query_params[param]
            
            # Rebuild clean URL
            from urllib.parse import urlencode, urlunparse
            clean_query = urlencode(clean_params, doseq=True) if clean_params else ''
            return urlunparse((parsed.scheme, parsed.netloc, parsed.path.rstrip('/'), 
                             parsed.params, clean_query, ''))
    except Exception:
        pass
    return url


def analyze(url: str):
    """Analyze LinkedIn URL for videos and images.
    
    Primary path uses yt-dlp via analyze_platform.
    If that fails (extractor breakage or site changes), fall back to
    a lightweight OpenGraph scrape to at least return an image or
    direct video URL when present.
    """
    normalized = _normalize_linkedin_url(url)
    try:
        return analyze_platform(normalized, PLATFORM_NAME, URL_PATTERNS)
    except Exception as e:
        # Fallback: Try OpenGraph tags (best-effort)
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept': '*/*',
                'Referer': 'https://www.linkedin.com/'
            }
            text = None
            try:
                import httpx  # type: ignore
                with httpx.Client(timeout=10, follow_redirects=True, headers=headers) as client:
                    r = client.get(normalized)
                    if r.status_code < 400:
                        text = r.text
            except Exception:
                text = None
            if text is None:
                try:
                    import requests  # type: ignore
                    r2 = requests.get(normalized, headers=headers, timeout=10)
                    if r2.status_code < 400:
                        text = r2.text
                
                # Helper moved outside try to avoid f-string regex quoting issues
                except Exception:
                    text = None
            if not text:
                raise ConnectionError(f"LinkedIn fetch failed: {e}")

            # Very small regex helpers for OpenGraph
            def _meta(prop: str):
                try:
                    pattern = r'<meta[^>]+property=["\']' + re.escape(prop) + r'["\'][^>]+content=["\']([^"\']+)["\']'
                    m = re.search(pattern, text, re.I)
                    return m.group(1) if m else None
                except Exception:
                    return None

            og_video = _meta('og:video:secure_url') or _meta('og:video:url') or _meta('og:video')
            og_image = _meta('og:image') or _meta('twitter:image')
            title = _meta('og:title') or 'LinkedIn Media'

            # Build minimal, frontend-compatible result
            if og_video:
                fmt = {
                    'format_id': 'direct-mp4',
                    'ext': 'MP4',
                    'quality': 'Video',
                    'resolution': None,
                    'height': None,
                    'fps': None,
                    'size': 'Unknown size',
                    'filesize_mb': None,
                    'url': og_video,
                    'has_direct_url': True,
                    'is_progressive': True,
                    'vcodec': None,
                    'acodec': None,
                    'tbr': None,
                    'type': 'video',
                    'source': 'opengraph'
                }
                item = {
                    'id': re.findall(r"(\d{8,})", normalized)[0] if re.search(r"(\d{8,})", normalized) else 'linkedin-media',
                    'title': title,
                    'thumbnail': og_image,
                    'duration': None,
                    'uploader': 'LinkedIn',
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
            if og_image:
                img = {
                    'format_id': 'img0',
                    'ext': 'jpg',
                    'width': None,
                    'height': None,
                    'url': og_image,
                    'filesize': None,
                    'type': 'image',
                    'quality': 'Image'
                }
                item = {
                    'id': re.findall(r"(\d{8,})", normalized)[0] if re.search(r"(\d{8,})", normalized) else 'linkedin-image',
                    'title': title,
                    'thumbnail': og_image,
                    'duration': None,
                    'uploader': 'LinkedIn',
                    'formats': [img],
                    'media_type': 'image'
                }
                return {
                    'title': item['title'],
                    'thumbnail': item['thumbnail'],
                    'duration': item['duration'],
                    'uploader': item['uploader'],
                    'media_type': item['media_type'],
                    'mp4': [],
                    'mp3': [],
                    'jpg': [img],
                    'images': [img],
                    'items': [item],
                    'count': 1,
                    'instant_available': False
                }
            # If neither is present, surface a 502 upstream error
            raise ConnectionError("LinkedIn: No media found via OpenGraph")
        except Exception as e2:
            # Map to ConnectionError so API returns 502 instead of 500
            raise ConnectionError(f"LinkedIn analyze failed: {e2}") from e


def prepare_download(url: str, format_id: str):
    normalized = _normalize_linkedin_url(url)
    if not any(p.search(normalized or "") for p in URL_PATTERNS):
        raise ValueError("Invalid LinkedIn URL")
    return prepare_download_options(normalized, format_id, PLATFORM_NAME)