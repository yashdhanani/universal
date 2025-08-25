#!/usr/bin/env python3
"""
Auto-check script (live):
- Starts the Flask app in background
- Streams important log lines live (auto-tune, downloader, optimize)
- Analyzes formats (measures analyze time)
- Starts a download
- Polls progress, detects first 'downloading' and 'Optimizing...' transitions
- Measures times: analyze, connect/queue, download, optimization, total
- Parses logs for size savings (if any)
- Cleans up the server process on exit
"""
import os
import sys
import time
import json
import signal
import subprocess
import threading
from datetime import datetime

import requests

BASE_URL = os.environ.get("DOWNLOADER_BASE_URL", "http://127.0.0.1:5000")
LOG_PATH = os.path.join(os.path.dirname(__file__), 'logs', 'app.log')
DOWNLOAD_URL = f"{BASE_URL}/api/download"
PROGRESS_URL_TMPL = f"{BASE_URL}/api/progress/{{task_id}}"
ANALYZE_URL = f"{BASE_URL}/api/youtube/analyze"

TEST_VIDEO = os.environ.get("TEST_VIDEO_URL", "https://www.youtube.com/watch?v=dQw4w9WgXcQ")

START_TIMEOUT = 40  # seconds to wait for server to become ready
POLL_INTERVAL = 1.0 # seconds between progress polls


def tail_log(path: str, stop_event: threading.Event):
    """Tail the log file and print selected lines live."""
    try:
        # Wait for file to exist
        for _ in range(80):
            if os.path.isfile(path):
                break
            if stop_event.is_set():
                return
            time.sleep(0.25)
        if not os.path.isfile(path):
            return
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            # Seek to end to only print new lines
            f.seek(0, os.SEEK_END)
            while not stop_event.is_set():
                line = f.readline()
                if not line:
                    time.sleep(0.25)
                    continue
                low = line.lower()
                if (
                    'auto_tune_aria2c' in low or
                    'using external downloader' in low or
                    '[auto-optimize]' in line or
                    'download request - url' in low or
                    'download completed successfully' in low
                ):
                    print("LOG ", line.rstrip())
    except Exception:
        pass


def wait_for_server(url: str, timeout: int = START_TIMEOUT) -> bool:
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = requests.get(url, timeout=2)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def spawn_server() -> subprocess.Popen:
    # Inherit current environment (includes AUTO_TUNE_ARIA2C / AUTO_OPTIMIZE vars if set by caller)
    cmd = [sys.executable, os.path.join(os.path.dirname(__file__), 'app.py')]
    proc = subprocess.Popen(cmd, cwd=os.path.dirname(__file__), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return proc


def safe_kill(proc: subprocess.Popen):
    try:
        if proc and proc.poll() is None:
            if os.name == 'nt':
                proc.terminate()
            else:
                proc.send_signal(signal.SIGTERM)
            try:
                proc.wait(timeout=10)
            except Exception:
                proc.kill()
    except Exception:
        pass


def pick_test_format() -> tuple[str, float]:
    """Pick a reasonable format selector and measure analyze time.
    Returns (format_id_or_selector, analyze_time_seconds).
    """
    t_start = datetime.now()
    try:
        r = requests.post(ANALYZE_URL, json={'url': TEST_VIDEO}, timeout=30)
        r.raise_for_status()
        data = r.json()
        formats = data.get('formats', [])
        # Prefer highest height
        best = None
        best_height = -1
        for f in formats:
            h = f.get('height') or 0
            if h > best_height:
                best = f
                best_height = h
        analyze_time = (datetime.now() - t_start).total_seconds()
        if best and best.get('format_id'):
            return best['format_id'], analyze_time
    except Exception:
        analyze_time = (datetime.now() - t_start).total_seconds()
        return 'bestvideo[height<=1080]+bestaudio/best', analyze_time
    # Fallback generic best selector
    analyze_time = (datetime.now() - t_start).total_seconds()
    return 'bestvideo[height<=1080]+bestaudio/best', analyze_time


def parse_optimize_savings(t_start_opt: datetime, t_finish: datetime):
    """Parse app.log between t_start_opt and t_finish for size savings."""
    if not os.path.isfile(LOG_PATH):
        return None
    fmt = "%Y-%m-%d %H:%M:%S,%f"
    comp_line = None
    try:
        with open(LOG_PATH, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                if '[auto-optimize] Completed:' in line:
                    try:
                        ts_str = line[:23]
                        ts = datetime.strptime(ts_str, fmt)
                        if t_start_opt <= ts <= t_finish:
                            comp_line = line.strip()
                    except Exception:
                        continue
    except Exception:
        return None

    if not comp_line:
        return None

    import re
    m = re.search(r"Completed:\s+([\d.]+) MB \u2192 ([\d.]+) MB", comp_line)
    if not m:
        m = re.search(r"Completed:\s+([\d.]+) MB .* ([\d.]+) MB", comp_line)
    if m:
        try:
            before = float(m.group(1))
            after = float(m.group(2))
            return before, after
        except Exception:
            return None
    return None


def main():
    print("🚀 Auto-check starting...")
    proc = spawn_server()
    log_stop = threading.Event()
    log_thread = threading.Thread(target=tail_log, args=(LOG_PATH, log_stop), daemon=True)
    log_thread.start()
    try:
        print("⏳ Waiting for server to be ready...")
        if not wait_for_server(BASE_URL, START_TIMEOUT):
            print("❌ Server did not become ready in time.")
            try:
                out = proc.stdout.read(4000).decode('utf-8', errors='ignore') if proc.stdout else ''
                print(out)
            except Exception:
                pass
            sys.exit(1)
        print("✅ Server ready")

        # Analyze formats
        fmt_selector, analyze_time = pick_test_format()
        print(f"🎯 Using format selector: {fmt_selector}")

        # Start download
        t_request = datetime.now()
        print(f"▶️  Requesting download at {t_request}")
        r = requests.post(DOWNLOAD_URL, json={'url': TEST_VIDEO, 'format_id': fmt_selector}, timeout=60)
        r.raise_for_status()
        task_id = r.json().get('task_id')
        if not task_id:
            print("❌ No task_id returned")
            sys.exit(1)
        print(f"🆔 task_id = {task_id}")

        # Poll progress
        t_first_downloading = None
        t_opt_start = None
        t_finish = None
        final_name = None
        while True:
            time.sleep(POLL_INTERVAL)
            pr = requests.get(PROGRESS_URL_TMPL.format(task_id=task_id), timeout=10)
            if pr.status_code != 200:
                print(f"⚠️ Progress HTTP {pr.status_code}")
                continue
            info = pr.json() or {}
            status = info.get('status')
            progress = info.get('progress') or ''
            if status == 'downloading' and t_first_downloading is None:
                t_first_downloading = datetime.now()
                print("🟢 Download started")
            if status == 'processing' and progress.lower().startswith('optimizing') and t_opt_start is None:
                t_opt_start = datetime.now()
                print("🟠 Optimization started")
            if status == 'finished':
                t_finish = datetime.now()
                final_name = info.get('filename')
                print(f"✅ Finished at {t_finish}")
                print(f"📄 Output: {final_name}")
                break
            if status == 'error' or info.get('error'):
                print(f"❌ Error: {info.get('error')}")
                sys.exit(2)

        # Compute timings
        total_time = (t_finish - t_request).total_seconds()
        connect_time = ((t_first_downloading or t_request) - t_request).total_seconds()
        if t_opt_start:
            download_time = (t_opt_start - (t_first_downloading or t_request)).total_seconds()
            optimize_time = (t_finish - t_opt_start).total_seconds()
        else:
            download_time = (t_finish - (t_first_downloading or t_request)).total_seconds()
            optimize_time = 0.0

        print("\n⏱️  Timing summary")
        print(f"- Analyze time: {analyze_time:.1f}s")
        print(f"- Connect/queue time: {connect_time:.1f}s")
        print(f"- Download time: {download_time:.1f}s")
        if optimize_time > 0:
            print(f"- Optimization time: {optimize_time:.1f}s")
        else:
            print(f"- Optimization: skipped (below threshold)")
        print(f"- Total time: {total_time:.1f}s")

        # Parse size savings if optimization ran
        savings = None
        before = after = None
        if t_opt_start:
            savings = parse_optimize_savings(t_opt_start, t_finish)
            if savings:
                before, after = savings
                print(f"📉 Size: {before:.1f} MB → {after:.1f} MB  (−{(before-after):.1f} MB, {(1-after/before)*100:.0f}% saved)")
            else:
                print("📉 Size savings: not found in logs (ensure logs/app.log is enabled and accessible)")

        # Write JSON report
        report = {
            'test_video': TEST_VIDEO,
            'task_id': task_id,
            'filename': final_name,
            'started_at': t_request.isoformat() if t_request else None,
            'finished_at': t_finish.isoformat() if t_finish else None,
            'timings': {
                'analyze': analyze_time,
                'connect_queue': connect_time,
                'download': download_time,
                'optimize': optimize_time,
                'total': total_time
            },
            'optimization': {
                'ran': bool(t_opt_start),
                'started_at': t_opt_start.isoformat() if t_opt_start else None,
                'size_before_mb': before,
                'size_after_mb': after,
                'savings_mb': (before - after) if (before is not None and after is not None) else None,
                'savings_percent': ((1 - (after / before)) * 100) if (before and after and before > 0) else None
            }
        }
        report_path = os.path.join(os.path.dirname(__file__), 'auto_check_report.json')
        try:
            with open(report_path, 'w', encoding='utf-8') as rf:
                json.dump(report, rf, ensure_ascii=False, indent=2)
            print(f"📝 Report written: {report_path}")
        except Exception as werr:
            print(f"⚠️ Failed to write report: {werr}")

        print("\n🎉 Auto-check complete")
        sys.exit(0)
    except requests.exceptions.RequestException as rexc:
        print(f"❌ HTTP error: {rexc}")
        sys.exit(3)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(4)
    finally:
        log_stop.set()
        try:
            log_thread.join(timeout=2)
        except Exception:
            pass
        safe_kill(proc)


if __name__ == '__main__':
    main()