#!/usr/bin/env python3
"""
Test multiple platform URLs against unified /api/info endpoint and report results.
- Uses base URL http://127.0.0.1:8000 by default (override with --base)
- For each URL, calls /api/info?url=...&instant=1
- Prints PASS with key details or FAIL with error summary
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import List, Dict, Any

import requests

DEFAULT_BASE = "http://127.0.0.1:8004"

# Collected test URLs from user message
TEST_URLS: List[str] = [
    # YouTube
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "https://www.youtube.com/shorts/aqz-KE-bpKQ",
    "https://www.youtube.com/playlist?list=PLMC9KNkIncKtsacKpgMb0CVqT5pXrWpKf",
    "https://www.youtube.com/@NASA",

    # Instagram
    "https://www.instagram.com/p/C8QltYbIh2P/",  # Photo
    "https://www.instagram.com/p/CWg8ZBxD5cf/",  # Carousel
    "https://www.instagram.com/p/CFkFyr0HT5G/",  # Video
    "https://www.instagram.com/reel/C9cP8s1yR3R/",  # Reel
    "https://www.instagram.com/tv/CFnU1OcJk5L/",   # IGTV
    "https://www.instagram.com/stories/highlights/17895511311129510/",  # Story highlight
    "https://www.instagram.com/p/CHuJ3FwJp4V/",  # Shopping post
    "https://www.instagram.com/nasa/",           # Profile
    "https://www.instagram.com/explore/locations/213385402/new-york-new-york/",  # Location
    "https://www.instagram.com/explore/tags/sunset/",  # Hashtag

    # Facebook
    "https://www.facebook.com/watch/?v=10153231379946729",
    "https://www.facebook.com/20531316728/posts/10154009990506729/",
    "https://www.facebook.com/media/set/?set=a.10100480647661891&type=3",
    "https://www.facebook.com/nasa",

    # TikTok
    "https://www.tiktok.com/@scout2015/video/6718335390845095173",
    "https://www.tiktok.com/@charlidamelio",
    "https://www.tiktok.com/tag/fyp",

    # Twitter (X)
    "https://twitter.com/nasa/status/1410624005669169154",
    "https://twitter.com/jack/status/20",
    "https://twitter.com/naval/status/1002103360646823936",
    "https://twitter.com/nasa",
    "https://twitter.com/hashtag/AI",

    # Pinterest
    "https://www.pinterest.com/pin/99360735500167749/",
    "https://www.pinterest.com/nasa/space/",
    "https://www.pinterest.com/nasa/",

    # Snapchat
    "https://www.snapchat.com/spotlight/WxPZ7VUrW3n",
    "https://www.snapchat.com/add/team.snapchat",

    # LinkedIn
    "https://www.linkedin.com/posts/linkedin_what-are-your-goals-activity-7010844765029011456-XYZ/",
    "https://www.linkedin.com/posts/ericschmidt_ai-and-society-activity-7048730381558749184-YsJK/",
    "https://www.linkedin.com/company/nasa/",
    "https://www.linkedin.com/pulse/future-work-jeff-weiner/",

    # Reddit
    "https://www.reddit.com/r/videos/comments/1c7dqk/sample_video_post/",
    "https://www.reddit.com/r/pics/comments/3g1jfi/cute_cat_picture/",
    "https://www.reddit.com/r/AskReddit/comments/1ajk3f/what_is_your_favorite_book/",
    "https://www.reddit.com/r/space/",

    # PDFs (general documents)
    "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf",
    "https://www.adobe.com/support/products/enterprise/knowledgecenter/media/c4611_sample_explain.pdf",
]


def friendly_title(s: str | None, max_len: int = 60) -> str:
    if not s:
        return "(no title)"
    s = s.replace("\n", " ").strip()
    return s if len(s) <= max_len else s[: max_len - 1] + "…"


def test_one(base: str, url: str) -> Dict[str, Any]:
    api = base.rstrip("/") + "/api/info"
    try:
        r = requests.get(api, params={"url": url, "instant": 1}, timeout=45)
    except Exception as e:
        return {"url": url, "status": "FAIL", "note": f"request error: {e}"}

    if r.status_code != 200:
        # Try to extract detail
        try:
            detail = r.json().get("detail")
        except Exception:
            detail = r.text[:200]
        return {"url": url, "status": "FAIL", "note": f"HTTP {r.status_code}: {detail}"}

    try:
        data = r.json()
    except Exception:
        return {"url": url, "status": "FAIL", "note": "invalid JSON"}

    media_type = data.get("media_type") or ("image" if not data.get("formats") else "video")
    title = friendly_title(data.get("title"))
    formats = data.get("formats") or []
    progressive = data.get("progressive_formats") or []
    images = data.get("images") or []

    # Decide PASS criteria:
    # - video: has at least 1 format or progressive format
    # - image: has images array or a thumbnail
    ok = False
    if media_type == "video":
        ok = len(formats) > 0 or len(progressive) > 0 or bool(data.get("url"))
    else:
        ok = len(images) > 0 or bool(data.get("thumbnail"))

    result = {
        "url": url,
        "status": "PASS" if ok else "FAIL",
        "title": title,
        "media_type": media_type,
        "formats": len(formats),
        "progressive": len(progressive),
        "images": len(images),
    }

    # Provide short note
    if ok:
        if media_type == "video":
            result["note"] = f"video: {len(formats)} fmts, {len(progressive)} progressive"
        else:
            result["note"] = f"image: {len(images)} images"
    else:
        result["note"] = "no extractable media"
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=DEFAULT_BASE, help="Base URL where main_api:APP is running")
    args = ap.parse_args()

    base = args.base
    print(f"Testing {len(TEST_URLS)} URLs against {base}/api/info")

    results: List[Dict[str, Any]] = []
    passed = failed = 0

    for url in TEST_URLS:
        res = test_one(base, url)
        results.append(res)
        status = res["status"]
        if status == "PASS":
            passed += 1
        else:
            failed += 1
        title = res.get("title") or ""
        media_type = res.get("media_type") or "?"
        note = res.get("note") or ""
        print(f"{status:4} | {media_type:5} | {url}\n      -> {title}\n      -> {note}")

    print("\nSummary:")
    print(f"  PASS: {passed}")
    print(f"  FAIL: {failed}")

    # Output JSON summary to stdout (last line) so it can be captured if needed
    summary = {
        "base": base,
        "total": len(TEST_URLS),
        "passed": passed,
        "failed": failed,
        "results": results,
    }
    print("\nJSON:")
    print(json.dumps(summary, ensure_ascii=False))

    # Exit non-zero if any failed (useful for CI)
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()