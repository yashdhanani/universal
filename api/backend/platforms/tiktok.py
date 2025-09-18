import re
from urllib.parse import urlparse, parse_qs
from .base import analyze_platform, prepare_download_options

PLATFORM_NAME = "tiktok"
# Match videos, profiles, hashtags (broader coverage)
URL_PATTERNS = [
    re.compile(r"https?://(www\.)?tiktok\.com/@[^/]+/video/\d+", re.I),
    re.compile(r"https?://(www\.)?tiktok\.com/@[^/]+/?$", re.I),
    re.compile(r"https?://(www\.)?tiktok\.com/tag/[^/]+/?$", re.I),
    re.compile(r"https?://vm\.tiktok\.com/\w+/?", re.I),
    re.compile(r"https?://vt\.tiktok\.com/\w+/?", re.I),
]


def _normalize_tiktok_url(url: str) -> str:
    """Normalize TikTok URLs: keep short links, strip trackers, lowercase host, trim trailing slash."""
    try:
        parsed = urlparse(url)
        host = (parsed.netloc or '').lower()
        # Keep official short redirectors as-is
        if any(domain in host for domain in ['vm.tiktok.com', 'vt.tiktok.com']):
            return url
        # Clean main tiktok.com URLs
        if 'tiktok.com' in host:
            query_params = parse_qs(parsed.query)
            clean_params = {}
            # Keep only occasionally-needed params
            keep_params = ['is_from_webapp', 'sender_device']
            for param in keep_params:
                if param in query_params:
                    clean_params[param] = query_params[param]
            from urllib.parse import urlencode, urlunparse
            clean_query = urlencode(clean_params, doseq=True) if clean_params else ''
            return urlunparse((parsed.scheme, host, parsed.path.rstrip('/'), parsed.params, clean_query, ''))
    except Exception:
        pass
    return url


def analyze(url: str):
    """Analyze TikTok URL for videos and images with broader URL support."""
    normalized = _normalize_tiktok_url(url)
    return analyze_platform(normalized, PLATFORM_NAME, URL_PATTERNS)


def prepare_download(url: str, format_id: str):
    normalized = _normalize_tiktok_url(url)
    if not any(p.search(normalized or "") for p in URL_PATTERNS):
        raise ValueError("Invalid TikTok URL")
    return prepare_download_options(normalized, format_id, PLATFORM_NAME)
