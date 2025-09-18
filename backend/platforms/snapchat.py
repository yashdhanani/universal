import re
from urllib.parse import urlparse
from .base import analyze_platform, prepare_download_options

PLATFORM_NAME = "snapchat"
# Stricter matching: story and spotlight links, plus short links
URL_PATTERNS = [
    re.compile(r"https?://story\.snapchat\.com/s/[A-Za-z0-9_-]+", re.I),
    re.compile(r"https?://(www\.)?snapchat\.com/add/[A-Za-z0-9_.-]+/story", re.I),
    re.compile(r"https?://(www\.)?snapchat\.com/spotlight/[A-Za-z0-9_-]+", re.I),
    re.compile(r"https?://t\.snapchat\.com/[A-Za-z0-9]+/?", re.I),
]


def _normalize_snapchat_url(url: str) -> str:
    """Clean Snapchat URLs for better extraction.
    Snapchat stories and spotlight content can have various URL formats.
    """
    try:
        parsed = urlparse(url)
        
        # Keep short URLs as-is
        if 't.snapchat.com' in parsed.netloc:
            return url
            
        # Clean path for consistency
        if 'snapchat.com' in parsed.netloc:
            return f"{parsed.scheme}://{parsed.netloc}{parsed.path.rstrip('/')}"
    except Exception:
        pass
    return url


def analyze(url: str):
    """Analyze Snapchat URL for videos and photos.
    
    Snapchat content includes:
    - Spotlight videos (short-form content)
    - Story photos and videos
    - Public snaps
    - Lens/filter content
    
    Note: Many Snapchat stories are photo-based!
    """
    normalized = _normalize_snapchat_url(url)
    return analyze_platform(normalized, PLATFORM_NAME, URL_PATTERNS)


def prepare_download(url: str, format_id: str):
    normalized = _normalize_snapchat_url(url)
    if not any(p.search(normalized or "") for p in URL_PATTERNS):
        raise ValueError("Invalid Snapchat URL")
    return prepare_download_options(normalized, format_id, PLATFORM_NAME)
