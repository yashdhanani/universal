import subprocess
import socket
import time

links = [
    # YouTube
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "https://youtube.com/shorts/aqz-KE-bpKQ",
    # Instagram
    "https://www.instagram.com/p/C8Ean7lM5F6/",
    "https://www.instagram.com/reel/C9hGuDnR8Qh/",
    # Facebook
    "https://www.facebook.com/watch/?v=10153231379946729",
    "https://www.facebook.com/photo/?fbid=10157283829081729",
    # TikTok
    "https://www.tiktok.com/@scout2015/video/6718335390845095173",
    # Twitter (X)
    "https://x.com/Interior/status/463440424141459456",
    "https://x.com/NASA/status/1415365457914288128",
    # Pinterest
    "https://www.pinterest.com/pin/99360735500167749/",
    # Snapchat (public test)
    "https://www.snapchat.com/add/test",
    # LinkedIn
    "https://www.linkedin.com/posts/linkedin_the-most-in-demand-hard-and-soft-skills-activity-6611509207500742656-HnQn/",
    # Reddit
    "https://www.reddit.com/r/videos/comments/9o9h8o/cute_puppy_video/",
    "https://www.reddit.com/r/pics/comments/9pfv38/puppy/"
]


# Set your proxy here (format: http://host:port or socks5://host:port)
proxy = "http://127.0.0.1:1080"  # Change this to your working proxy

summary = []

def check_connectivity(host, port=443, timeout=10):
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False

def get_domain(url):
    try:
        return url.split('//')[1].split('/')[0]
    except Exception:
        return None

import os
import glob

def is_photo_link(url):
    # crude check for photo links by platform
    photo_domains = [
        ("instagram.com", "/p/"),
        ("facebook.com", "/photo"),
        ("twitter.com", "/photo"),
        ("x.com", "/photo"),
        ("pinterest.com", "/pin/"),
        ("reddit.com", "/pics/"),
    ]
    for dom, path in photo_domains:
        if dom in url and path in url:
            return True
    return False

def preview_latest_image():
    # Find the most recent jpg/png/webp in current dir and open it
    exts = ('*.jpg', '*.jpeg', '*.png', '*.webp')
    files = []
    for ext in exts:
        files.extend(glob.glob(ext))
    if not files:
        print("No image file found for preview.")
        return
    latest = max(files, key=os.path.getctime)
    print(f"Previewing image: {latest}")
    os.startfile(latest)

for url in links:
    print(f"\nTesting: {url}")
    domain = get_domain(url)
    connectivity = check_connectivity(domain) if domain else False
    if not connectivity:
        print(f"[NETWORK ERROR] Cannot connect to {domain}. Check your network, VPN, or firewall settings.")
        summary.append((url, "Network Error"))
        continue
    try:
        start = time.time()
        # Use proper CLI subcommand: download
        if "tiktok.com" in url:
            args = [
                "python", "cli.py", "download", url, "--proxy", proxy, "-f", "best"
            ]
            result = subprocess.run(args, capture_output=True, text=True, timeout=180)
        elif is_photo_link(url):
            # Try bestimage for photo links
            args = ["python", "cli.py", "download", url, "-f", "bestimage"]
            if "instagram.com" in url:
                args = ["python", "cli.py", "download", url, "--browser", "chrome", "-f", "bestimage"]
            result = subprocess.run(args, capture_output=True, text=True, timeout=180)
        elif "instagram.com" in url:
            args = [
                "python", "cli.py", "download", url, "--browser", "chrome", "-f", "best"
            ]
            result = subprocess.run(args, capture_output=True, text=True, timeout=180)
        else:
            args = [
                "python", "cli.py", "download", url, "-f", "best"
            ]
            result = subprocess.run(args, capture_output=True, text=True, timeout=180)
        elapsed = time.time() - start
        status = "Success" if result.returncode == 0 else f"Failed (code {result.returncode})"
        print("Status:", status)
        print("Time:", f"{elapsed:.1f}s")
        if result.stdout.strip():
            print("Output:", result.stdout.strip())
        if result.stderr.strip():
            print("Error:", result.stderr.strip())
        # TikTok-specific advice
        if "tiktok.com" in url and ("timeout" in result.stderr.lower() or result.returncode != 0):
            print(f"[TIKTOK ERROR] If you see a timeout, try using a VPN or proxy. TikTok may be blocked in your region or by your ISP. Proxy used: {proxy}")
        # Instagram-specific advice
        if "instagram.com" in url and ("empty media response" in result.stderr.lower() or result.returncode != 0):
            print("[INSTAGRAM ERROR] Instagram may require authentication. Make sure your cookies.txt is up to date and valid. See https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp")
        # Preview photo if downloaded
        if is_photo_link(url) and status == "Success":
            preview_latest_image()
        summary.append((url, status))
    except Exception as e:
        print(f"Exception: {e}")
        summary.append((url, f"Exception: {e}"))

print("\n--- SUMMARY ---")
for url, status in summary:
    print(f"{url} => {status}")
with open("batch_test_results.log", "w", encoding="utf-8") as f:
    for url, status in summary:
        f.write(f"{url} => {status}\n")
