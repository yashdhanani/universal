import re
from .base import analyze_platform, prepare_download_options

PLATFORM_NAME = "naver"
URL_PATTERNS = [
    re.compile(r"https?://(?:www\.)?naver\.com/", re.I),
    re.compile(r"https?://(?:tv|video)\.naver\.com/", re.I),
    re.compile(r"https?://m\.naver\.com/", re.I),
]


def analyze(url: str):
    """Analyze Naver URLs via generic base analyzer.
    Returns normalized formats allowing instant streaming where possible.
    """
    return analyze_platform(url, PLATFORM_NAME, URL_PATTERNS)


def prepare_download(url: str, format_id: str):
    """Prefer instant/direct streaming for progressive MP4 or audio-only.
    Falls back to yt-dlp options when needed (merge handled by base).
    """
    return prepare_download_options(url, format_id, PLATFORM_NAME)