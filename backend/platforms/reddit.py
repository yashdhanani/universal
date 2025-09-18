import re
from urllib.parse import urlparse, parse_qs
from .base import analyze_platform, prepare_download_options

PLATFORM_NAME = "reddit"
# Stricter matching: post permalinks and direct media hosts
URL_PATTERNS = [
    # Post comments permalink
    re.compile(r"https?://(www\.|old\.|new\.|np\.)?reddit\.com/r/[^/]+/comments/[a-z0-9]+(/[^/]+)?(/\w+)?/?", re.I),
    # Short post link
    re.compile(r"https?://redd\.it/\w+/?", re.I),
    # Direct media hosts
    re.compile(r"https?://v\.redd\.it/\w+", re.I),
    re.compile(r"https?://i\.redd\.it/[^\s]+", re.I),
]


def _normalize_reddit_url(url: str) -> str:
    """Clean Reddit URLs for better extraction.
    Reddit has various URL formats and tracking parameters.
    """
    try:
        parsed = urlparse(url)
        
        # Keep short URLs as-is
        if 'redd.it' in parsed.netloc:
            return url
            
        # Normalize subdomain to www for consistency
        if 'reddit.com' in parsed.netloc:
            netloc = parsed.netloc.lower()
            if netloc.startswith(('old.', 'new.', 'np.')):
                netloc = 'www.reddit.com'
            elif not netloc.startswith('www.'):
                netloc = 'www.reddit.com'
            
            # Strip all query/fragment for canonical post URLs
            from urllib.parse import urlunparse
            return urlunparse((parsed.scheme, netloc, parsed.path.rstrip('/'), '', '', ''))
    except Exception:
        pass
    return url


def analyze(url: str):
    """Analyze Reddit URL for videos and images.
    
    Primary path uses yt-dlp. If it fails (e.g., unsupported embedded hosts
    or extractor issues), fall back to OpenGraph scraping to at least return
    an image preview or a direct video URL when present.
    """
    normalized = _normalize_reddit_url(url)
    try:
        return analyze_platform(normalized, PLATFORM_NAME, URL_PATTERNS)
    except Exception as e:
        # Fallback: try OpenGraph tags on the Reddit page
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept': '*/*',
                'Referer': 'https://www.reddit.com/'
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
                except Exception:
                    text = None
            if not text:
                raise ConnectionError(f"Reddit fetch failed: {e}")

            def _meta(prop: str):
                try:
                    pattern = r'<meta[^>]+property=["\']' + re.escape(prop) + r'["\'][^>]+content=["\']([^"\']+)["\']'
                    m = re.search(pattern, text, re.I)
                    return m.group(1) if m else None
                except Exception:
                    return None

            og_video = _meta('og:video:secure_url') or _meta('og:video:url') or _meta('og:video')
            og_image = _meta('og:image') or _meta('twitter:image')
            title = _meta('og:title') or 'Reddit Media'

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
                    'id': re.findall(r"/comments/([a-z0-9]+)/", normalized)[0] if re.search(r"/comments/([a-z0-9]+)/", normalized) else 'reddit-media',
                    'title': title,
                    'thumbnail': og_image,
                    'duration': None,
                    'uploader': 'Reddit',
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
                    'id': re.findall(r"/comments/([a-z0-9]+)/", normalized)[0] if re.search(r"/comments/([a-z0-9]+)/", normalized) else 'reddit-image',
                    'title': title,
                    'thumbnail': og_image,
                    'duration': None,
                    'uploader': 'Reddit',
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
            raise ConnectionError("Reddit: No media found via OpenGraph")
        except Exception as e2:
            # Map to ConnectionError so API returns 502 rather than 500
            raise ConnectionError(f"Reddit analyze failed: {e2}") from e


def prepare_download(url: str, format_id: str):
    normalized = _normalize_reddit_url(url)
    if not any(p.search(normalized or "") for p in URL_PATTERNS):
        raise ValueError("Invalid Reddit URL")
    return prepare_download_options(normalized, format_id, PLATFORM_NAME)