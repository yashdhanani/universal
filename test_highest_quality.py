#!/usr/bin/env python3
import requests
import time
from datetime import datetime

BASE = "http://127.0.0.1:5000"
TEST_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
SELECTOR = "bestvideo[height<=4320]+bestaudio/best/best[acodec!=none][vcodec!=none]"

def start_download(url):
    r = requests.post(f"{BASE}/api/download", json={"url": url, "format_id": SELECTOR}, timeout=60)
    r.raise_for_status()
    data = r.json()
    return data.get("task_id")


def wait_for_completion(task_id, timeout=600):
    t0 = time.time()
    last = None
    while time.time() - t0 < timeout:
        pr = requests.get(f"{BASE}/api/progress/{task_id}", timeout=15)
        pr.raise_for_status()
        info = pr.json()
        status = info.get("status")
        if status != last:
            print(f"- Status: {status} | {info.get('progress','')}")
            last = status
        if status == "finished":
            return True, info.get("filename")
        if status == "error":
            return False, info.get("error")
        time.sleep(2)
    return False, "timeout"


def main():
    print("Highest Quality Test:", datetime.now().strftime("%H:%M:%S"))
    # Server check
    rs = requests.get(BASE, timeout=5)
    assert rs.status_code == 200

    task_id = start_download(TEST_URL)
    print("Task:", task_id)
    ok, info = wait_for_completion(task_id)
    if ok:
        ext = info.split('.')[-1].lower() if info and '.' in info else ''
        print("SUCCESS:", info, "| ext=", ext)
    else:
        print("FAILED:", info)

if __name__ == "__main__":
    main()