import yt_dlp
import re
import json
import os
from typing import Optional, Dict, Any

from .base import build_ydl_opts

try:
    import requests  # type: ignore
except Exception:
    requests = None  # type: ignore


def _pick_progressive_mp4(formats: list[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Choose the best progressive MP4 (has both audio and video)."""
    best = None
    for f in formats or []:
        try:
            ext = (f.get('ext') or '').lower()
            if ext != 'mp4':
                continue
            if (f.get('acodec') == 'none') or (f.get('vcodec') == 'none'):
                continue
            if not f.get('url'):
                continue
            # Prefer highest height
            if best is None or (f.get('height') or 0) > (best.get('height') or 0):
                best = f
        except Exception:
            continue
    return best


def _load_cookies_cookiejar(platform: str = 'facebook'):
    """Load cookies for requests from auth_manager if available (Netscape format)."""
    try:
        from backend.auth_manager import auth_manager
        cookies_file = auth_manager.get_cookies_file(platform)
        if not cookies_file or not requests:
            return None
        jar = requests.cookies.RequestsCookieJar()
        with open(cookies_file, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                if not line or line.startswith('#') or line.strip() == '':
                    continue
                parts = line.strip().split('\t')
                if len(parts) != 7:
                    continue
                domain, flag, path, secure, expires, name, value = parts
                secure_bool = (secure.lower() == 'true') if isinstance(secure, str) else False
                try:
                    jar.set(name, value, domain=domain, path=path, secure=secure_bool)
                except Exception:
                    continue
        return jar
    except Exception:
        return None


def _scrape_facebook_mp4(url: str) -> Optional[str]:
    """Scrape Facebook page for direct MP4 when extractor is broken.
    Looks for playable_url_quality_hd/playable_url or hd_src/sd_src in HTML/JSON.
    """
    if not requests:
        return None
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': 'https://www.facebook.com/'
    }
    cookies = _load_cookies_cookiejar('facebook')
    try:
        resp = requests.get(url, headers=headers, cookies=cookies, timeout=15)
        html = resp.text or ''
    except Exception:
        return None

    # Strategy 1: Find JSON with playable_url[_quality_hd]
    # Common keys: playable_url, playable_url_quality_hd, browser_native_sd_url, browser_native_hd_url
    candidates = []
    try:
        for m in re.finditer(r'\{[^{}]*"playable_url[^"]*"\s*:\s*"(https?:\\/\\/[^"\\]+)"[^}]*\}', html):
            try:
                url_escaped = m.group(1)
                cand = url_escaped.encode('utf-8').decode('unicode_escape').replace('\\/', '/')
                candidates.append(cand)
            except Exception:
                continue
    except Exception:
        pass

    # Also look for hd/sd src keys
    try:
        for key in ('playable_url_quality_hd', 'browser_native_hd_url', 'hd_src', 'browser_native_sd_url', 'sd_src', 'playable_url'):
            pattern = rf'"{key}"\s*:\s*"(https?:\\/\\/[^"\\]+\.mp4[^"\\]*)"'
            for m in re.finditer(pattern, html):
                try:
                    cand = m.group(1).encode('utf-8').decode('unicode_escape').replace('\\/', '/')
                    candidates.append(cand)
                except Exception:
                    continue
    except Exception:
        pass

    # Prefer HD-looking URLs
    def _score(u: str) -> int:
        score = 0
        if 'hd' in u: score += 2
        if '.mp4' in u: score += 1
        if 'fbcdn' in u: score += 1
        return score

    candidates = [c for c in candidates if c.startswith('http')]
    if candidates:
        candidates.sort(key=_score, reverse=True)
        return candidates[0]
    return None


def get_facebook_mp4(url: str) -> str:
    """
    Return a direct progressive MP4 URL (with audio) for a Facebook video when available.
    Primary: yt-dlp. Fallback: HTML scrape for playable_url/hd_src.
    To skip yt-dlp entirely, set FACEBOOK_SCRAPE_ONLY=1 in environment.
    """
    scrape_only = os.environ.get('FACEBOOK_SCRAPE_ONLY', '').strip() in ('1', 'true', 'True', 'YES', 'yes', 'on')

    # Primary path via yt-dlp unless scrape-only
    if not scrape_only:
        try:
            ydl_opts = build_ydl_opts({
                'skip_download': True,
                # Ask yt-dlp to prefer progressive MP4 first
                'format': 'best[ext=mp4][acodec!=none][vcodec!=none]/best[ext=mp4]/best',
                'http_headers': {
                    'Referer': 'https://www.facebook.com/'
                }
            }, platform='facebook')

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

            # Handle playlists/entries
            if info and info.get('_type') == 'playlist':
                entries = info.get('entries') or []
                if entries:
                    info = entries[0]

            if info:
                # Try progressive MP4 from formats
                best_prog = _pick_progressive_mp4(info.get('formats') or [])
                if best_prog and best_prog.get('url'):
                    return best_prog['url']

                # Fallback: some extractors place direct URL at top-level
                top_url = info.get('url')
                top_ext = (info.get('ext') or '').lower()
                if top_url and (not top_ext or top_ext == 'mp4'):
                    return top_url
        except Exception:
            # Swallow and try scraper fallback
            pass

    # Secondary path via HTML scraping
    scraped = _scrape_facebook_mp4(url)
    if scraped:
        return scraped

    raise ValueError('No direct MP4 URL available for instant download')