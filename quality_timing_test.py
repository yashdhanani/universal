#!/usr/bin/env python3
"""
Measure analyze (fetch) and full download times for each distinct height using both APIs.
- URL: provided via CLI arg or defaults to Rick Astley
- Prefers MP4; falls back to any when MP4 unavailable
- Outputs console summary

Usage:
  python quality_timing_test.py --url <youtube_url>

Requires the server running at http://127.0.0.1:5000
"""
import argparse
import time
import requests
from collections import defaultdict

BASE = "http://127.0.0.1:5000"

def analyze_standard(url):
    t0 = time.time()
    r = requests.post(f"{BASE}/api/video_info", json={"url": url}, timeout=60)
    dt = time.time() - t0
    r.raise_for_status()
    data = r.json()
    return data, dt

def analyze_universal(url):
    t0 = time.time()
    r = requests.post(f"{BASE}/api/youtube/analyze", json={"url": url}, timeout=60)
    dt = time.time() - t0
    r.raise_for_status()
    data = r.json()
    return data, dt

def pick_formats_by_height(formats):
    # Bucket by height and prefer MP4/H.264 when possible
    by_h = {}
    for f in formats:
        h = f.get('height')
        if not h:
            # Try derive from resolution
            res = f.get('resolution') or f.get('resolution_str') or f.get('resolution_text')
            if isinstance(res, str) and 'x' in res:
                try:
                    h = int(res.split('x')[-1])
                except Exception:
                    h = None
        if not h:
            continue
        cur = by_h.get(h)
        if cur is None:
            by_h[h] = f
        else:
            def score(fmt):
                ext = (fmt.get('ext') or '').lower()
                vcodec = (fmt.get('vcodec') or '')
                s = 0
                if ext == 'mp4': s += 3
                if vcodec.startswith('avc1'): s += 2
                # Prefer higher tbr/fps
                s += (fmt.get('fps') or 0)/100.0
                s += (fmt.get('tbr') or 0)/1000.0
                return s
            if score(f) > score(cur):
                by_h[h] = f
    # Return sorted by height ascending
    return [by_h[h] for h in sorted(by_h.keys())]

def start_download_standard(url, format_id):
    t0 = time.time()
    r = requests.post(f"{BASE}/api/download", json={"url": url, "format_id": format_id}, timeout=60)
    dt = time.time() - t0
    r.raise_for_status()
    return r.json().get('task_id'), dt

def start_download_universal(url, format_id):
    t0 = time.time()
    r = requests.post(f"{BASE}/api/youtube/download", json={"url": url, "format_id": format_id}, timeout=60)
    dt = time.time() - t0
    r.raise_for_status()
    return r.json().get('task_id'), dt

def wait_for_task(task_id, max_wait=900):
    # Poll until completed/failed/timeout. Return total elapsed.
    t0 = time.time()
    last_status = ''
    while True:
        if time.time() - t0 > max_wait:
            return {'status': 'timeout', 'elapsed': time.time()-t0}
        try:
            r = requests.get(f"{BASE}/api/progress/{task_id}", timeout=10)
            if r.status_code != 200:
                time.sleep(2)
                continue
            data = r.json()
            status = data.get('status')
            if status and status != last_status:
                last_status = status
            if status in ('completed','finished','failed'):
                return {'status': status, 'elapsed': time.time()-t0}
        except Exception:
            time.sleep(2)
        time.sleep(2)

def run(url):
    print("== Standard API analyze ==")
    std_info, std_analyze = analyze_standard(url)
    print(f"Analyze: {std_analyze:.2f}s, formats={len(std_info.get('formats',[]))}")
    std_formats = std_info.get('formats', [])
    std_selected = pick_formats_by_height(std_formats)
    print(f"Heights found (standard): {[f.get('height') for f in std_selected]}")

    print("\n== Universal API analyze ==")
    uni_info, uni_analyze = analyze_universal(url)
    print(f"Analyze: {uni_analyze:.2f}s, formats={len(uni_info.get('formats',[]))}")
    uni_formats = uni_info.get('formats', [])
    uni_selected = pick_formats_by_height(uni_formats)
    print(f"Heights found (universal): {[f.get('height') for f in uni_selected]}")

    # Download each height for both APIs
    results = []

    def measure_set(label, selected, starter):
        for f in selected:
            fmt_id = f.get('format_id')
            h = f.get('height')
            print(f"\n{label} -> Start download height={h}, id={fmt_id}")
            task_id, init_time = starter(url, fmt_id)
            print(f"Task: {task_id}, init={init_time:.2f}s")
            fin = wait_for_task(task_id)
            print(f"Status: {fin['status']}, total={fin['elapsed']:.2f}s")
            results.append({
                'api': label,
                'height': h,
                'format_id': fmt_id,
                'init_time_s': round(init_time,2),
                'total_time_s': round(fin['elapsed'],2),
                'status': fin['status']
            })

    print("\n== Download via Standard API ==")
    measure_set('standard', std_selected, start_download_standard)

    print("\n== Download via Universal API ==")
    measure_set('universal', uni_selected, start_download_universal)

    # Summary
    print("\n==== SUMMARY (MP4 preferred) ====")
    for r in results:
        print(f"[{r['api']}] {r['height']}p id={r['format_id']} init={r['init_time_s']}s total={r['total_time_s']}s status={r['status']}")

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--url', default='https://youtu.be/JgDNFQ2RaLQ?si=uhw46pxHgbds1T81')
    args = ap.parse_args()
    run(args.url)