import re
from urllib.parse import urlparse, urlunparse
from .base import analyze_platform, prepare_download_options

PLATFORM_NAME = "instagram"
URL_PATTERNS = [
    # Base domains
    re.compile(r"https?://(www\.)?instagram\.com/", re.I),
    re.compile(r"https?://instagr\.am/", re.I),

    # Posts, reels, tv, stories
    re.compile(r"https?://(www\.)?instagram\.com/(p|reel|reels|tv|stories)/", re.I),

    # Profiles (single segment paths like /username)
    re.compile(r"https?://(www\.)?instagram\.com/[^/]+/?$", re.I),

    # Hashtags
    re.compile(r"https?://(www\.)?instagram\.com/explore/tags/[^/]+/?", re.I),

    # Locations
    re.compile(r"https?://(www\.)?instagram\.com/explore/locations/\d+(/[^/]+)?/?", re.I),
]


def _normalize_instagram_url(url: str) -> str:
    """Normalize Instagram URLs to a canonical form.
    Rules:
    - Always https scheme
    - Always host www.instagram.com (rewrite instagr.am and any *.instagram.com)
    - Strip query string and fragment
    - Preserve case for post/reel/tv/stories IDs
    - Lowercase for profiles (/username), hashtags, and locations paths
    - Validate profiles strictly via username regex [A-Za-z0-9._]{1,30}
    """
    try:
        p = urlparse(url)
        # Canonical scheme and host
        scheme = "https"
        netloc_in = (p.netloc or "").lower()
        if netloc_in == "instagr.am":
            netloc = "www.instagram.com"
        elif netloc_in.endswith("instagram.com"):
            netloc = "www.instagram.com"
        else:
            # Not an Instagram domain; return original unmodified
            return url

        path = (p.path or "").rstrip('/')

        # Posts / Reels / TV / Stories (IDs can be case-sensitive; keep as-is)
        if re.search(r"^/(?:p|reel|reels|tv|stories)/", path, re.I):
            return urlunparse((scheme, netloc, path, '', '', ''))

        # Profiles: exactly one segment like /username and must match allowed regex
        # Instagram usernames: [A-Za-z0-9._]{1,30}
        if re.match(r"^/[A-Za-z0-9._]{1,30}$", path):
            return urlunparse((scheme, netloc, path.lower(), '', '', ''))

        # Hashtags (e.g., /explore/tags/ai) → case-insensitive, normalize to lowercase
        if re.match(r"^/explore/tags/[^/]+$", path, re.I):
            return urlunparse((scheme, netloc, path.lower(), '', '', ''))

        # Locations (e.g., /explore/locations/123/new-york) → slug may vary in case; normalize to lowercase
        if re.match(r"^/explore/locations/\d+(?:/[^/]+)?$", path, re.I):
            return urlunparse((scheme, netloc, path.lower(), '', '', ''))

        # Fallback: return canonicalized scheme/host and stripped query/fragment
        return urlunparse((scheme, netloc, path, '', '', ''))

    except Exception:
        pass
    return url


def analyze(url: str):
    normalized = _normalize_instagram_url(url)
    info = analyze_platform(normalized, PLATFORM_NAME, URL_PATTERNS)

    # Ensure thumbnail_url exists for frontend preview
    if info is None:
        return None

    if isinstance(info, dict):
        thumb = (
            info.get("thumbnail")
            or info.get("thumbnail_url")
            or info.get("display_url")
            or (
                info.get("display_resources", [{}])[-1].get("src")
                if isinstance(info.get("display_resources"), list)
                else None
            )
        )
        # Always set thumbnail_url, falling back to default icon
        info["thumbnail_url"] = thumb or "/static/og-default.svg"
        return info

    # Unexpected type, return as-is
    return info


def prepare_download(url: str, format_id: str):
    normalized = _normalize_instagram_url(url)
    return prepare_download_options(normalized, format_id, PLATFORM_NAME)
