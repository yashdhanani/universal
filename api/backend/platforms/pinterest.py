import re
from urllib.parse import urlparse, parse_qs
from .base import analyze_platform, prepare_download_options

PLATFORM_NAME = "pinterest"
# Stricter matching: pin pages and short links
URL_PATTERNS = [
    re.compile(r"https?://(www\.)?pinterest\.com/pin/\d+/?", re.I),
    re.compile(r"https?://pin\.it/\w+/?", re.I),
]


def _normalize_pinterest_url(url: str) -> str:
    """Clean Pinterest URLs for optimal extraction.
    Pinterest URLs often have tracking and can be shortened via pin.it.
    """
    try:
        parsed = urlparse(url)
        
        # pin.it URLs are fine as-is, yt-dlp will resolve them
        if 'pin.it' in parsed.netloc:
            return url
            
        # For pinterest.com URLs, clean tracking params
        if 'pinterest.com' in parsed.netloc:
            # Remove tracking parameters
            query_params = parse_qs(parsed.query)
            clean_params = {}
            
            # Keep essential params for pin identification
            keep_params = []  # Pinterest pins usually don't need query params
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
    """Analyze Pinterest URL for images.
    
    Pinterest is primarily image-focused:
    - Individual pins (single high-res images)
    - Board collections (multiple images)
    - Story pins (multiple images/videos)
    
    This makes Pinterest perfect for testing the photo workflow!
    """
    normalized = _normalize_pinterest_url(url)
    return analyze_platform(normalized, PLATFORM_NAME, URL_PATTERNS)


def prepare_download(url: str, format_id: str):
    normalized = _normalize_pinterest_url(url)
    if not any(p.search(normalized or "") for p in URL_PATTERNS):
        raise ValueError("Invalid Pinterest URL")
    return prepare_download_options(normalized, format_id, PLATFORM_NAME)
