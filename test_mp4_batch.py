#!/usr/bin/env python3
import requests
import time
import sys
from datetime import datetime

BASE = "http://127.0.0.1:5000"
TEST_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

# Presets to test, prefer MP4/H.264 + M4A
PRESETS = [
    (144, None),
    (240, None),
    (360, None),
    (480, None),
    (720, 60),
    (1080, 60),
]

# Known progressive MP4s
PROGRESSIVE = {
    360: "18",   # 360p mp4
    720: "22",   # 720p mp4
}

def start_download_for(height, fps=None):
    # Prefer a strict mp4 selector with avc1+m4a; fallback to progressive mp4 ids
    if height in PROGRESSIVE and (fps is None or fps <= (720 if height==720 else 30)):
        selector = PROGRESSIVE[height]
    else:
        fps_filter = f"[fps>={fps}]" if isinstance(fps, int) else ""
        selector = (
            f"bestvideo[ext=mp4][vcodec^=avc1][height={height}]{fps_filter}+bestaudio[ext=m4a]/"
            f"best[ext=mp4][height={height}]{fps_filter}/"
            f"best[acodec!=none][vcodec!=none][height<={height}]"
        )
    r = requests.post(f"{BASE}/api/download", json={"url": TEST_URL, "format_id": selector}, timeout=90)
    r.raise_for_status()
    return r.json()["task_id"], selector


def wait_task(task_id, timeout=240):
    t0 = time.time()
    last_status = None
    while time.time() - t0 < timeout:
        pr = requests.get(f"{BASE}/api/progress/{task_id}", timeout=10)
        pr.raise_for_status()
        data = pr.json()
        status = data.get("status")
        if status != last_status:
            print(f"  - Status: {status} | {data.get('progress','')} ")
            last_status = status
        if status == "finished":
            return True, data.get("filename")
        if status == "error":
            return False, data.get("error")
        time.sleep(2)
    return False, "timeout"


def main():
    print("MP4 Batch Test starting at", datetime.now().strftime("%H:%M:%S"))
    # Quick server check
    try:
        rs = requests.get(BASE, timeout=5)
        assert rs.status_code == 200
    except Exception as e:
        print("Server not reachable:", e)
        sys.exit(1)

    results = []
    for height, fps in PRESETS:
        label = f"{height}p" + (f"{fps}" if fps else "")
        print(f"\n▶ Testing {label} (MP4-preferred)")
        try:
            task_id, selector = start_download_for(height, fps)
            print(f"  Selector: {selector}")
            ok, info = wait_task(task_id)
            if ok:
                ext = (info.split('.')[-1].lower() if info and '.' in info else '')
                results.append((label, True, info, ext))
                print(f"  ✓ Finished: {info}")
            else:
                results.append((label, False, info, ''))
                print(f"  ✗ Failed: {info}")
        except Exception as e:
            results.append((label, False, str(e), ''))
            print(f"  ✗ Error: {e}")

    print("\n=== SUMMARY ===")
    for label, ok, info, ext in results:
        status = "OK" if ok else "FAIL"
        print(f"{label:8} -> {status} | {info} | ext={ext}")

if __name__ == "__main__":
    main()