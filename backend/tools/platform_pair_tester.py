#!/usr/bin/env python3
"""
Platform Pair Tester
- Tests two sample URLs per platform against /api/v2/{platform}/info
- Optional: also probe /api/v2/{platform}/instant (format_id=best)
- Default base: http://127.0.0.1:8004 (override with --base)

Usage:
  python tools/platform_pair_tester.py --base http://127.0.0.1:8004 --instant
"""
from __future__ import annotations

import argparse
import sys
from typing import Dict, List, Tuple

import requests

DEFAULT_BASE = "http://127.0.0.1:5000"
TIMEOUT = 45

# Two example URLs per platform. Some may require public/unauthenticated access.
PLATFORM_URLS: Dict[str, Tuple[str, str]] = {
    # YouTube
    "youtube": (
        "https://www.youtube.com/watch?v=BaW_jenozKc",  # yt-dlp test video
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    ),
    # Instagram (public posts are safer; private or region-locked may fail)
    "instagram": (
        "https://www.instagram.com/p/C8QltYbIh2P/",
        "https://www.instagram.com/reel/C9cP8s1yR3R/",
    ),
    # Facebook (server-side full task disabled; Instant is recommended)
    "facebook": (
        "https://www.facebook.com/watch/?v=10153231379946729",
        "https://www.facebook.com/20531316728/posts/10154009990506729/",
    ),
    # TikTok
    "tiktok": (
        "https://www.tiktok.com/@scout2015/video/6718335390845095173",
        "https://www.tiktok.com/@scout2015/video/6718335390845095173",  # duplicate stable sample
    ),
    # Twitter/X
    "twitter": (
        "https://twitter.com/nasa/status/1410624005669169154",
        "https://twitter.com/naval/status/1002103360646823936",
    ),
    # Pinterest
    "pinterest": (
        "https://www.pinterest.com/pin/99360735500167749/",
        "https://www.pinterest.com/nasa/space/",
    ),
    # Snapchat (public spotlight/account)
    "snapchat": (
        "https://www.snapchat.com/spotlight/WxPZ7VUrW3n",
        "https://www.snapchat.com/add/team.snapchat",
    ),
    # LinkedIn (public posts or company pages)
    "linkedin": (
        "https://www.linkedin.com/posts/linkedin_what-are-your-goals-activity-7010844765029011456-XYZ/",
        "https://www.linkedin.com/company/nasa/",
    ),
    # Reddit
    "reddit": (
        "https://www.reddit.com/r/videos/comments/1c7dqk/sample_video_post/",
        "https://www.reddit.com/r/pics/comments/3g1jfi/cute_cat_picture/",
    ),
}


def pass_from_info_json(data: dict) -> bool:
    """Heuristic PASS check for /info responses."""
    if not isinstance(data, dict):
        return False
    media_type = data.get("media_type") or ("image" if not data.get("formats") else "video")
    if media_type == "video":
        return bool(data.get("formats") or data.get("progressive_formats") or data.get("url"))
    return bool(data.get("images") or data.get("thumbnail"))


def test_info(base: str, platform: str, url: str) -> Tuple[str, str]:
    api = base.rstrip("/") + f"/api/v2/{platform}/info"
    try:
        r = requests.get(api, params={"url": url}, timeout=TIMEOUT)
    except Exception as e:
        return ("FAIL", f"request error: {e}")

    if r.status_code != 200:
        note = None
        try:
            note = r.json().get("detail")
        except Exception:
            note = r.text[:200]
        return ("FAIL", f"HTTP {r.status_code}: {note}")

    try:
        data = r.json()
    except Exception:
        return ("FAIL", "invalid JSON")

    ok = pass_from_info_json(data)
    title = (data.get("title") or "").strip().replace("\n", " ")[:80]
    if ok:
        return ("PASS", f"{title}")
    return ("FAIL", f"no extractable media; title={title}")


def test_instant(base: str, platform: str, url: str) -> Tuple[str, str]:
    api = base.rstrip("/") + f"/api/v2/{platform}/instant"
    try:
        # Disable redirects to detect Location for direct links
        r = requests.get(api, params={"url": url, "format_id": "best"}, timeout=TIMEOUT, allow_redirects=False)
    except Exception as e:
        return ("FAIL", f"instant request error: {e}")

    # Treat 302/303 with Location as PASS (redirect to media)
    if r.status_code in (301, 302, 303, 307, 308) and r.headers.get("Location"):
        return ("PASS", f"redirect -> {r.headers.get('Location')[:80]}")

    # 200 OK: treat streaming media as PASS (video/audio or octet-stream)
    if r.status_code == 200:
        ctype = (r.headers.get("Content-Type") or "").lower()
        if any(ctype.startswith(p) for p in ("video/", "audio/")) or ctype in ("application/octet-stream", "application/mp4"):
            return ("PASS", f"streaming ({ctype or 'unknown content-type'})")
        # Some implementations may return JSON with direct url
        try:
            data = r.json()
            if isinstance(data, dict) and data.get("url"):
                return ("PASS", "direct url in JSON")
        except Exception:
            pass
        # Fallback: look for MP4/WebM magic in body
        sig = r.content[:8]
        if sig.startswith(b"ftyp") or sig.startswith(b"\x1A\x45\xDF\xA3") or sig.startswith(b"ID3"):
            return ("PASS", "binary media stream")
        return ("FAIL", f"instant HTTP 200 but not media; body={r.text[:120]}")

    return ("FAIL", f"instant HTTP {r.status_code}: {r.text[:120]}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=DEFAULT_BASE, help="API base URL (e.g., http://127.0.0.1:8004)")
    ap.add_argument("--instant", action="store_true", help="Also probe /instant (format_id=best)")
    args = ap.parse_args()

    base = args.base
    do_instant = args.instant

    print(f"Testing 2 URLs per platform against {base}/api/v2/{{platform}}/info")
    if do_instant:
        print("Also probing /instant with format_id=best (no-follow redirects)")

    total = passed = failed = 0
    for platform, pair in PLATFORM_URLS.items():
        print(f"\n== {platform.upper()} ==")
        for idx, url in enumerate(pair, start=1):
            total += 1
            status, note = test_info(base, platform, url)
            print(f"[{idx}] INFO   {status:4} | {url}\n      -> {note}")
            if status == "PASS":
                passed += 1
            else:
                failed += 1

            if do_instant:
                istatus, inote = test_instant(base, platform, url)
                print(f"      INSTANT {istatus:4} | {inote}")
                if istatus == "PASS":
                    passed += 1
                else:
                    failed += 1
                total += 1

    print("\nSummary:")
    print(f"  Total checks: {total}")
    print(f"  PASS: {passed}")
    print(f"  FAIL: {failed}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())