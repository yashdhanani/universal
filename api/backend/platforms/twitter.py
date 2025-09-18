import re
from urllib.parse import urlparse, parse_qs
from .base import analyze_platform, prepare_download_options

PLATFORM_NAME = "twitter"
# Stricter matching: only tweet permalinks
URL_PATTERNS = [
    re.compile(r"https?://(www\.)?(twitter\.com|x\.com)/([^/]+)/status/\d+", re.I),
    re.compile(r"https?://(www\.)?(twitter\.com|x\.com)/i/status/\d+", re.I),
]


def _normalize_twitter_url(url: str) -> str:
    """Clean Twitter/X URLs for better extraction.
    Remove tracking parameters and normalize between twitter.com and x.com.
    """
    try:
        parsed = urlparse(url)
        
        # Normalize domain (yt-dlp handles both, but consistency helps caching)
        netloc = parsed.netloc.lower()
        if 'x.com' in netloc:
            netloc = netloc.replace('x.com', 'twitter.com')
        elif 'twitter.com' in netloc:
            pass  # Keep as twitter.com
        
        # Remove tracking parameters but keep essential ones
        query_params = parse_qs(parsed.query)
        clean_params = {}
        
        # Keep essential params for tweet identification
        keep_params = ['s', 't']  # Share tracking can sometimes be needed
        for param in keep_params:
            if param in query_params:
                clean_params[param] = query_params[param]
        
        # Rebuild clean URL
        from urllib.parse import urlencode, urlunparse
        clean_query = urlencode(clean_params, doseq=True) if clean_params else ''
        return urlunparse((parsed.scheme, netloc, parsed.path.rstrip('/'), 
                         parsed.params, clean_query, ''))
    except Exception:
        pass
    return url


def analyze(url: str):
    """Analyze Twitter/X URL for videos and images.
    
    Twitter posts can contain:
    - Single videos (native or external)
    - Single images
    - Multiple images (up to 4 in a tweet)
    - GIFs (treated as videos)
    - Quoted tweets with media
    """
    normalized = _normalize_twitter_url(url)
    return analyze_platform(normalized, PLATFORM_NAME, URL_PATTERNS)


def prepare_download(url: str, format_id: str):
    normalized = _normalize_twitter_url(url)
    if not any(p.search(normalized or "") for p in URL_PATTERNS):
        raise ValueError("Invalid Twitter URL")
    return prepare_download_options(normalized, format_id, PLATFORM_NAME)
