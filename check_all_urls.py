#!/usr/bin/env python3
"""
Check all 41 URLs against your local /api/info endpoint and produce:
- Console PASS/FAIL summary (similar to prior logs)
- JSON report written to tools/reports/check_all_urls.json
- Optional side-by-side diff vs a baseline report/log

Enhancements:
- Retries with exponential backoff for transient errors (timeouts, connection resets)
- Per-domain timeouts (longer for restricted platforms by default)
- Parallel execution with stable, ordered output

Usage:
  python check_all_urls.py \
    --base http://127.0.0.1:8004/api/info \
    --timeout 60 \
    --public-timeout 45 \
    --restricted-timeout 90 \
    --retries 2 \
    --retry-backoff 1.5 \
    --concurrency 6 \
    --outfile tools/reports/check_all_urls.json \
    --baseline tools/reports/run_with_cookies.json

Notes:
- instant=1 is sent to trigger the fast path if your backend supports it
- Server-side cookies are used if your backend is configured with COOKIES_FILE
- If --baseline is omitted, the latest JSON file in tools/reports is used (excluding outfile)
"""
from __future__ import annotations
import argparse
import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import urlparse

import requests
from requests.exceptions import Timeout, ConnectionError as ReqConnectionError

DEFAULT_BASE = os.environ.get("INFO_BASE", "http://127.0.0.1:8004/api/info")
DEFAULT_TIMEOUT = int(os.environ.get("INFO_TIMEOUT", "60"))
DEFAULT_PUBLIC_TIMEOUT = int(os.environ.get("INFO_PUBLIC_TIMEOUT", "45"))
DEFAULT_RESTRICTED_TIMEOUT = int(os.environ.get("INFO_RESTRICTED_TIMEOUT", "90"))
DEFAULT_OUTFILE = os.environ.get("INFO_OUTFILE", "tools/reports/check_all_urls.json")
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


def _effective_timeout(url: str, default_timeout: int, public_timeout: int, restricted_timeout: int) -> int:
    label = label_url(url)
    if label == "restricted":
        return restricted_timeout or default_timeout
    if label == "public":
        return public_timeout or default_timeout
    return default_timeout


def _request_with_retry(base: str, url: str, timeout: int, retries: int, backoff: float) -> Tuple[Optional[requests.Response], Optional[str]]:
    """Do GET with retry on timeouts/connection errors. Returns (response, error_str)."""
    attempt = 0
    delay = 0.0
    last_err: Optional[str] = None
    while attempt <= retries:
        if delay > 0:
            time.sleep(delay)
        try:
            r = requests.get(base, params={"url": url, "instant": 1}, timeout=timeout)
            return r, None
        except (Timeout, ReqConnectionError) as e:
            last_err = f"retryable error: {e}"
            delay = max(0.0, (delay or 0.5) * backoff)  # exponential backoff
            attempt += 1
            continue
        except Exception as e:
            return None, str(e)
    return None, last_err or "unknown retryable error"


def _find_latest_report(reports_dir: str, exclude_path: Optional[str]) -> Optional[str]:
    try:
        files = []
        for name in os.listdir(reports_dir):
            full = os.path.join(reports_dir, name)
            if exclude_path and os.path.abspath(full) == os.path.abspath(exclude_path):
                continue
            if os.path.isfile(full) and name.lower().endswith(".json"):
                files.append((os.path.getmtime(full), full))
        if not files:
            return None
        files.sort(reverse=True)
        return files[0][1]
    except Exception:
        return None


def _parse_baseline(baseline_path: str) -> Dict[str, Dict[str, Any]]:
    """Return mapping url -> {status, title, http_status}. Supports JSON reports and PASS/FAIL text logs."""
    mapping: Dict[str, Dict[str, Any]] = {}
    try:
        with open(baseline_path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
        # Try JSON first
        try:
            data = json.loads(text)
            if isinstance(data, dict) and "results" in data and isinstance(data["results"], list):
                for item in data["results"]:
                    url = item.get("url")
                    if not url:
                        continue
                    mapping[url] = {
                        "status": item.get("status"),
                        "title": item.get("title"),
                        "http_status": item.get("http_status"),
                    }
                return mapping
        except Exception:
            pass
        # Fallback: parse PASS/FAIL lines like "PASS | label | URL" then next line has -> title/HTTP
        # Regex to capture: (PASS|FAIL) | ... | (URL)
        line_re = re.compile(r"^(PASS|FAIL)\s*\|.*?\|\s*(https?://\S+)\s*$", re.MULTILINE)
        title_re = re.compile(r"^\s*->\s*(.+)$", re.MULTILINE)
        lines = text.splitlines()
        for i, line in enumerate(lines):
            m = line_re.match(line)
            if not m:
                continue
            status = m.group(1)
            url = m.group(2)
            # Look ahead for a title/HTTP line
            title = None
            for j in range(i + 1, min(i + 4, len(lines))):
                mt = title_re.match(lines[j])
                if mt:
                    title = mt.group(1).strip()
                    break
            mapping[url] = {"status": status, "title": title}
    except Exception:
        pass
    return mapping


def _diff_results(current: List[Dict[str, Any]], baseline_map: Dict[str, Dict[str, Any]]):
    improved = []  # FAIL -> PASS
    regressed = []  # PASS -> FAIL
    unchanged_pass = []
    unchanged_fail = []
    new_urls = []  # not in baseline
    removed_urls = []  # in baseline but not current

    baseline_urls = set(baseline_map.keys())
    current_urls = {r["url"] for r in current}

    for r in current:
        url = r["url"]
        cur_status = r["status"]
        base = baseline_map.get(url)
        if not base:
            new_urls.append(url)
            continue
        base_status = base.get("status")
        if base_status == "FAIL" and cur_status == "PASS":
            improved.append(url)
        elif base_status == "PASS" and cur_status == "FAIL":
            regressed.append(url)
        elif cur_status == "PASS":
            unchanged_pass.append(url)
        else:
            unchanged_fail.append(url)

    for url in (baseline_urls - current_urls):
        removed_urls.append(url)

    return {
        "improved": improved,
        "regressed": regressed,
        "unchanged_pass": unchanged_pass,
        "unchanged_fail": unchanged_fail,
        "new": new_urls,
        "removed": removed_urls,
    }


def _process_one(index: int, base: str, url: str, timeout: int, retries: int, backoff: float) -> Dict[str, Any]:
    tag = label_url(url)
    start = time.time()
    status = "FAIL"
    http_status: Optional[int] = None
    title: Optional[str] = None
    error: Optional[str] = None

    resp: Optional[requests.Response]
    resp, err = _request_with_retry(base, url, timeout=timeout, retries=retries, backoff=backoff)
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
    parser = argparse.ArgumentParser(description="Check 41 URLs via /api/info")
    parser.add_argument("--base", default=DEFAULT_BASE, help="Base /api/info endpoint")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="Default request timeout (seconds)")
    parser.add_argument("--public-timeout", type=int, default=DEFAULT_PUBLIC_TIMEOUT, help="Timeout for public domains (seconds)")
    parser.add_argument("--restricted-timeout", type=int, default=DEFAULT_RESTRICTED_TIMEOUT, help="Timeout for restricted domains (seconds)")
    parser.add_argument("--retries", type=int, default=DEFAULT_RETRIES, help="Retry count for timeouts/connection errors")
    parser.add_argument("--retry-backoff", type=float, default=DEFAULT_BACKOFF, help="Backoff multiplier between retries")
    parser.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY, help="Max parallel requests")
    parser.add_argument("--outfile", default=DEFAULT_OUTFILE, help="Path to JSON report output")
    parser.add_argument("--baseline", default=None, help="Path to baseline report/log for diff; default = latest JSON in tools/reports")
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

    # Submit in parallel but keep output stable by collecting then printing in order
    futures = []
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        for i, url in enumerate(URLS):
            eff_timeout = _effective_timeout(url, timeout_default, timeout_public, timeout_restricted)
            futures.append(executor.submit(_process_one, i, base, url, eff_timeout, retries, backoff))

        # Collect results
        results_list: List[Optional[Dict[str, Any]]] = [None] * len(URLS)
        for fut in as_completed(futures):
            res = fut.result()
            results_list[res["index"]] = res

    # Print ordered output and aggregate
    results: List[Dict[str, Any]] = []
    totals = {"PASS": 0, "FAIL": 0}

    for res in results_list:
        assert res is not None
        print(f"{res['status']} | {res['label']:9} | {res['url']}")
        print(f"      -> {res['title'] or (('HTTP ' + str(res['http_status'])) if res['http_status'] else 'ERROR')} ")
        if res["status"] == "FAIL" and res.get("error"):
            print(f"      -> {res['error']}")
        totals[res["status"]] += 1
        # Remove index from persisted result
        rcopy = dict(res)
        rcopy.pop("index", None)
        results.append(rcopy)

    summary = {
        "base": base,
        "generated_at": int(time.time()),
        "totals": totals,
        "results": results,
    }

    with open(outfile, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print("\nSummary:")
    print(json.dumps(totals, indent=2))
    print(f"Report written to: {outfile}")

    # Diff vs baseline
    baseline_path = args.baseline
    if baseline_path is None:
        baseline_path = _find_latest_report(os.path.join("tools", "reports"), exclude_path=outfile)
        if baseline_path:
            print(f"Using latest baseline: {baseline_path}")
    if baseline_path and os.path.exists(baseline_path):
        base_map = _parse_baseline(baseline_path)
        diff = _diff_results(results, base_map)
        diff_path = os.path.splitext(outfile)[0] + ".diff.json"
        with open(diff_path, "w", encoding="utf-8") as f:
            json.dump(diff, f, ensure_ascii=False, indent=2)

        total_improved = len(diff["improved"])
        total_regressed = len(diff["regressed"])
        print("\nDiff vs baseline:")
        print(json.dumps({
            "improved": total_improved,
            "regressed": total_regressed,
            "unchanged_pass": len(diff["unchanged_pass"]),
            "unchanged_fail": len(diff["unchanged_fail"]),
            "new": len(diff["new"]),
            "removed": len(diff["removed"]),
        }, indent=2))

        if diff["regressed"]:
            print("\nRegressions:")
            for u in diff["regressed"]:
                print(f" - {u}")
        if diff["improved"]:
            print("\nImprovements:")
            for u in diff["improved"]:
                print(f" - {u}")
        print(f"Diff written to: {diff_path}")
    else:
        if baseline_path:
            print(f"Baseline not found or unreadable: {baseline_path}")

    # Return non-zero if any FAIL
    return 0 if totals["FAIL"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())