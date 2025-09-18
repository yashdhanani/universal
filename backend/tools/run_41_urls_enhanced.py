#!/usr/bin/env python3
"""
Enhanced 41-URL runner for unified /api/info with instant fast-path.
- Auto-sets multi=1 for YouTube playlists/channels/@user and Instagram posts/profiles.
- Per-platform timeouts and retries with exponential backoff.
- Produces tools/reports/run_41_urls_enhanced.json

Usage:
  python tools/run_41_urls_enhanced.py \
    --base http://127.0.0.1:8004/api/info \
    --timeout 60 \
    --public-timeout 45 \
    --restricted-timeout 90 \
    --retries 2 \
    --retry-backoff 1.5 \
    --concurrency 6 \
    --outfile tools/reports/run_41_urls_enhanced.json
"""
from __future__ import annotations
import argparse
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import urlparse

import requests
from requests.exceptions import Timeout, ConnectionError as ReqConnectionError

DEFAULT_BASE = os.environ.get("INFO_BASE", "http://127.0.0.1:8000/api/info")
DEFAULT_TIMEOUT = int(os.environ.get("INFO_TIMEOUT", "60"))
DEFAULT_PUBLIC_TIMEOUT = int(os.environ.get("INFO_PUBLIC_TIMEOUT", "45"))
DEFAULT_RESTRICTED_TIMEOUT = int(os.environ.get("INFO_RESTRICTED_TIMEOUT", "90"))
DEFAULT_OUTFILE = os.environ.get("INFO_OUTFILE", "tools/reports/run_41_urls_enhanced.json")
DEFAULT_RETRIES = int(os.environ.get("INFO_RETRIES", "2"))
DEFAULT_BACKOFF = float(os.environ.get("INFO_RETRY_BACKOFF", "1.5"))
DEFAULT_CONCURRENCY = int(os.environ.get("INFO_CONCURRENCY", "6"))

URLS: List[str] = [
    # YouTube
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "https://www.youtube.com/shorts/aqz-KE-bpKQ",
    "https://www.youtube.com/playlist?list=PLMC9KNkIncKtsacKpgMb0CVqT5pXrWpKf",
    "https://www.youtube.com/@NASA",

    # Instagram
    "https://www.instagram.com/p/C8QltYbIh2P/",
    "https://www.instagram.com/p/CWg8ZBxD5cf/",
    "https://www.instagram.com/p/CFkFyr0HT5G/",
    "https://www.instagram.com/reel/C9cP8s1yR3R/",
    "https://www.instagram.com/tv/CFnU1OcJk5L/",
    "https://www.instagram.com/stories/highlights/17895511311129510/",
    "https://www.instagram.com/p/CHuJ3FwJp4V/",
    "https://www.instagram.com/nasa/",
    "https://www.instagram.com/explore/locations/213385402/new-york-new-york/",
    "https://www.instagram.com/explore/tags/sunset/",

    # Facebook
    "https://www.facebook.com/watch/?v=10153231379946729",
    "https://www.facebook.com/20531316728/posts/10154009990506729/",
    "https://www.facebook.com/media/set/?set=a.10100480647661891&type=3",
    "https://www.facebook.com/nasa",

    # TikTok
    "https://www.tiktok.com/@scout2015/video/6718335390845095173",
    "https://www.tiktok.com/@charlidamelio",
    "https://www.tiktok.com/tag/fyp",

    # Twitter
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

    # PDFs
    "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf",
    "https://www.adobe.com/support/products/enterprise/knowledgecenter/media/c4611_sample_explain.pdf",
]

RESTRICTED_DOMAINS = (
    "instagram.com",
    "facebook.com",
    "tiktok.com",
    "twitter.com",
    "x.com",
    "pinterest.com",
    "snapchat.com",
    "linkedin.com",
)

PUBLIC_HINT_DOMAINS = (
    "youtube.com",
    "youtu.be",
    "reddit.com",
    "w3.org",
    "adobe.com",
)


def label_url(url: str) -> str:
    host = urlparse(url).netloc.lower()
    if any(d in host for d in RESTRICTED_DOMAINS):
        return "restricted"
    if any(d in host for d in PUBLIC_HINT_DOMAINS):
        return "public"
    return "unknown"


def needs_multi(url: str) -> bool:
    host = urlparse(url).netloc.lower()
    path = urlparse(url).path.lower()
    if "youtube.com" in host or host in ("youtu.be", "m.youtube.com"):
        return ("list=" in url.lower()) or any(seg in path for seg in ("/playlist", "/channel/", "/c/", "/user/", "/@"))
    if "instagram.com" in host:
        # posts, profiles, reels, tv, stories can hold multiple or need multi view
        return any(seg in path for seg in ("/p/", "/reel/", "/tv/", "/stories/", "/explore/", "/tags/")) or path.rstrip("/").count("/") <= 2
    return False


def effective_timeout(url: str, default_timeout: int, public_timeout: int, restricted_timeout: int) -> int:
    label = label_url(url)
    if label == "restricted":
        return restricted_timeout or default_timeout
    if label == "public":
        return public_timeout or default_timeout
    return default_timeout


def request_with_retry(base: str, url: str, timeout: int, retries: int, backoff: float) -> Tuple[Optional[requests.Response], Optional[str]]:
    attempt = 0
    delay = 0.0
    last_err: Optional[str] = None
    params = {"url": url, "instant": 1}
    if needs_multi(url):
        params["multi"] = 1
    while attempt <= retries:
        if delay > 0:
            time.sleep(delay)
        try:
            r = requests.get(base, params=params, timeout=timeout)
            return r, None
        except (Timeout, ReqConnectionError) as e:
            last_err = f"retryable error: {e}"
            delay = max(0.0, (delay or 0.5) * backoff)
            attempt += 1
            continue
        except Exception as e:
            return None, str(e)
    return None, last_err or "unknown retryable error"


def process_one(index: int, base: str, url: str, timeout: int, retries: int, backoff: float) -> Dict[str, Any]:
    tag = label_url(url)
    start = time.time()
    status = "FAIL"
    http_status: Optional[int] = None
    title: Optional[str] = None
    error: Optional[str] = None

    resp: Optional[requests.Response]
    resp, err = request_with_retry(base, url, timeout=timeout, retries=retries, backoff=backoff)
    if resp is not None:
        http_status = resp.status_code
        if resp.status_code == 200:
            status = "PASS"
            try:
                data = resp.json()
            except Exception:
                data = {}
            title = (
                data.get("title")
                or data.get("webpage_title")
                or (data.get("result", {}) if isinstance(data.get("result"), dict) else {}).get("title")
                or "N/A"
            )
        else:
            error = (resp.text or "").strip()[:200]
    else:
        error = err

    duration_ms = int((time.time() - start) * 1000)

    return {
        "index": index,
        "url": url,
        "label": tag,
        "status": status,
        "http_status": http_status,
        "title": title,
        "error": error,
        "duration_ms": duration_ms,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Enhanced 41-URL run via /api/info with auto-multi")
    parser.add_argument("--base", default=DEFAULT_BASE, help="Base /api/info endpoint")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="Default request timeout (seconds)")
    parser.add_argument("--public-timeout", type=int, default=DEFAULT_PUBLIC_TIMEOUT, help="Timeout for public domains (seconds)")
    parser.add_argument("--restricted-timeout", type=int, default=DEFAULT_RESTRICTED_TIMEOUT, help="Timeout for restricted domains (seconds)")
    parser.add_argument("--retries", type=int, default=DEFAULT_RETRIES, help="Retry count for timeouts/connection errors")
    parser.add_argument("--retry-backoff", type=float, default=DEFAULT_BACKOFF, help="Backoff multiplier between retries")
    parser.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY, help="Max parallel requests")
    parser.add_argument("--outfile", default=DEFAULT_OUTFILE, help="Path to JSON report output")
    args = parser.parse_args()

    base = args.base.rstrip("/")
    timeout_default = args.timeout
    timeout_public = args.public_timeout
    timeout_restricted = args.restricted_timeout
    retries = args.retries
    backoff = args.retry_backoff
    concurrency = max(1, args.concurrency)
    outfile = args.outfile
    os.makedirs(os.path.dirname(outfile), exist_ok=True)

    cookies_file = os.environ.get("COOKIES_FILE") or os.environ.get("COOKIES_PATH")

    print(f"Testing {len(URLS)} URLs against {base}")
    if cookies_file:
        print(f"Using server-side cookies (if backend is configured): {cookies_file}")
    print(f"Concurrency: {concurrency}")
    print(f"Timeouts: public={timeout_public}s, restricted={timeout_restricted}s, default={timeout_default}s")
    if retries > 0:
        print(f"Retry policy: retries={retries}, backoff={backoff}")

    results: List[Dict[str, Any]] = []
    futures = []
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        for idx, u in enumerate(URLS):
            tout = effective_timeout(u, timeout_default, timeout_public, timeout_restricted)
            futures.append(executor.submit(process_one, idx, base, u, tout, retries, backoff))
        for f in as_completed(futures):
            results.append(f.result())

    results.sort(key=lambda r: r["index"])  # stable order

    summary = {
        "base": base,
        "results": results,
        "pass": sum(1 for r in results if r["status"] == "PASS"),
        "fail": sum(1 for r in results if r["status"] == "FAIL"),
        "generated_at": int(time.time()),
    }

    import json
    with open(outfile, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(f"\nSaved report to {outfile}")
    print(f"PASS: {summary['pass']}  FAIL: {summary['fail']}")

    return 0 if summary["fail"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())