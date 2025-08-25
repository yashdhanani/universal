import re
import os
import shutil
import json
import yt_dlp
from flask import Flask, request, jsonify, send_file, send_from_directory, render_template, redirect, url_for, flash, abort, Response, stream_with_context
from werkzeug.exceptions import NotFound
import threading 
import uuid
from datetime import datetime
import time
import logging
import subprocess

# Setup logging to console and rotating file
from logging.handlers import RotatingFileHandler
LOG_DIR = os.path.join(os.path.dirname(__file__), 'logs')
os.makedirs(LOG_DIR, exist_ok=True)
log_path = os.path.join(LOG_DIR, 'app.log')

logger = logging.getLogger('yt_downloader')
logger.setLevel(logging.INFO)

# Console handler
_console = logging.StreamHandler()
_console.setLevel(logging.INFO)
_console.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))

# File handler (5 MB x 3 backups)
_file = RotatingFileHandler(log_path, maxBytes=5 * 1024 * 1024, backupCount=3, encoding='utf-8')
_file.setLevel(logging.INFO)
_file.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))

# Attach handlers once
if not logger.handlers:
    logger.addHandler(_console)
    logger.addHandler(_file)


def network_retry_wrapper(func, max_retries=3, delay=2):
    """Wrapper to retry network operations with exponential backoff"""
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            error_str = str(e).lower()
            if any(keyword in error_str for keyword in ['getaddrinfo failed', 'network', 'dns', 'timeout', 'connection']):
                if attempt < max_retries - 1:
                    wait_time = delay * (2 ** attempt)
                    logger.warning(f"Network error (attempt {attempt + 1}/{max_retries}): {str(e)[:100]}...")
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                    continue
            raise e
    return None


# Format caching for performance
import hashlib
from functools import lru_cache
import threading

# Enhanced in-memory cache for video formats (expires after 5 minutes)
format_cache = {}
cache_lock = threading.Lock()
CACHE_DURATION = 300  # 5 minutes

# Performance optimization: pre-compiled regex for faster filtering
import re
HLS_PATTERN = re.compile(r'm3u8|hls', re.IGNORECASE)
PREMIUM_PATTERN = re.compile(r'premium|storyboard', re.IGNORECASE)

CACHE_VERSION = 'v2'

def get_cache_key(url):
    """Generate cache key for URL (include version to bust stale caches)"""
    return hashlib.md5(f"{url}|{CACHE_VERSION}".encode()).hexdigest()

def get_cached_formats(url):
    """Get cached formats if available and not expired"""
    cache_key = get_cache_key(url)
    
    with cache_lock:
        if cache_key in format_cache:
            cached_data, timestamp = format_cache[cache_key]
            if time.time() - timestamp < CACHE_DURATION:
                logger.info(f"Using cached formats for {url[:50]}...")
                return cached_data
            else:
                # Remove expired cache
                del format_cache[cache_key]
    
    return None

def cache_formats(url, data):
    """Cache formats for future use"""
    cache_key = get_cache_key(url)
    
    with cache_lock:
        format_cache[cache_key] = (data, time.time())
        logger.info(f"Cached formats for {url[:50]}...")

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your_secret_key_change_in_production')
# Use absolute path for downloads to avoid any path confusion
DOWNLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'downloads')
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# Prefer speed over exhaustive discovery (can be overridden with env)
PREFER_SPEED = os.environ.get('PREFER_SPEED', '1') == '1'

# Auto-tune ARIA2C threads at startup (Hetzner test) and persist to .env
AUTO_TUNE_ARIA2C = os.environ.get('AUTO_TUNE_ARIA2C', '0') == '1'


def _persist_env_var(key, value, dotenv_path=os.path.join(os.path.dirname(__file__), '.env')):
    """Create/update a .env file with key=value. Keep existing entries and comments."""
    try:
        lines = []
        if os.path.exists(dotenv_path):
            with open(dotenv_path, 'r', encoding='utf-8') as f:
                lines = f.read().splitlines()
        found = False
        new_lines = []
        for line in lines:
            if not line.strip() or line.strip().startswith('#'):
                new_lines.append(line)
                continue
            k = line.split('=', 1)[0].strip()
            if k == key:
                new_lines.append(f"{key}={value}")
                found = True
            else:
                new_lines.append(line)
        if not found:
            new_lines.append(f"{key}={value}")
        with open(dotenv_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(new_lines) + '\n')
        logger.info(f"Persisted {key} to {dotenv_path}")
    except Exception as e:
        logger.warning(f"Failed to persist {key} to .env: {e}")


def _map_mbps_to_threads(mbps: float | None) -> int:
    if mbps is None:
        return 32
    if mbps < 10:
        return 8
    if mbps < 50:
        return 16
    if mbps < 200:
        return 32
    return 64


def _auto_tune_aria2c_threads():
    if not AUTO_TUNE_ARIA2C:
        return
    # Respect explicit env override
    if os.environ.get('ARIA2C_THREADS'):
        logger.info("AUTO_TUNE_ARIA2C enabled but ARIA2C_THREADS already set; skipping auto-tune.")
        return
    try:
        import urllib.request
        test_url = os.environ.get('ARIA2C_TEST_URL', 'https://speed.hetzner.de/10MB.bin')
        req = urllib.request.Request(test_url, headers={'User-Agent': 'Mozilla/5.0'})
        start = time.time()
        total = 0
        timeout = 10
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            # Read for ~3 seconds to estimate throughput without downloading all
            chunk_size = 1024 * 1024
            while True:
                if time.time() - start > 3.0:
                    break
                data = resp.read(chunk_size)
                if not data:
                    break
                total += len(data)
        elapsed = max(time.time() - start, 0.001)
        bps = total / elapsed
        mbps = bps * 8 / 1_000_000
        threads = _map_mbps_to_threads(mbps)
        os.environ['ARIA2C_THREADS'] = str(threads)
        logger.info(f"AUTO_TUNE_ARIA2C: measured ~{mbps:.1f} Mbps over {elapsed:.2f}s, choosing ARIA2C_THREADS={threads}")
        _persist_env_var('ARIA2C_THREADS', str(threads))
    except Exception as e:
        logger.warning(f"AUTO_TUNE_ARIA2C failed: {e}")


# Run auto-tune before computing the default threads variable
_auto_tune_aria2c_threads()

# Configurable aria2c concurrency (default 32 if not tuned)
ARIA2C_THREADS = int(os.environ.get('ARIA2C_THREADS', '32'))

# Auto video optimization settings
AUTO_OPTIMIZE = os.environ.get('AUTO_OPTIMIZE', '1') == '1'
AUTO_OPTIMIZE_THRESHOLD_MB = int(os.environ.get('AUTO_OPTIMIZE_THRESHOLD', '50'))
FFMPEG_PRESET = os.environ.get('FFMPEG_PRESET', 'veryfast')
CRF = os.environ.get('CRF', '23')

tasks = {}
TASK_CLEANUP_INTERVAL = 3600  # Clean up every hour
TASK_MAX_AGE = 7200           # Remove tasks older than 2 hours

def cleanup_old_tasks():
    """Periodically cleans up old tasks from the in-memory dictionary to prevent memory leaks."""
    while True:
        time.sleep(TASK_CLEANUP_INTERVAL)
        now = datetime.now()
        # Create a list of keys to delete to avoid modifying dict while iterating
        tasks_to_delete = [
            task_id for task_id, data in list(tasks.items())
            if data.get('last_update') and (now - data['last_update']).total_seconds() > TASK_MAX_AGE
        ]
        
        if tasks_to_delete:
            logger.info(f"Cleaning up {len(tasks_to_delete)} old tasks from memory.")
            for task_id in tasks_to_delete:
                tasks.pop(task_id, None)



# Optional: path to cookies file for YouTube; export cookies from your browser to this file if needed
COOKIES_FILE = os.environ.get('COOKIES_FILE', os.path.join(os.path.dirname(__file__), 'cookies.txt'))


def build_ydl_opts(overrides=None):
    """Build minimal, fast yt-dlp options for optimal performance.
    Based on tested working configuration.
    """
    opts = {
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
        'socket_timeout': 15,  # Faster timeout
        'retries': 2,  # Minimal retries for speed
        # Speed optimizations for downloads
        'concurrent_fragment_downloads': 4,
        'http_chunk_size': 10485760,  # 10MB chunks
        'sleep_interval': 0,  # No delays
        'max_sleep_interval': 0,
        # Stabilize requests with a modern desktop UA and headers
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9'
        }
    }
    # Optional: ffmpeg path from environment (absolute folder or binary path)
    ffmpeg_loc = os.environ.get('FFMPEG_LOCATION') or os.environ.get('FFMPEG_PATH')
    if ffmpeg_loc and (os.path.isabs(ffmpeg_loc) and (os.path.isdir(ffmpeg_loc) or os.path.isfile(ffmpeg_loc))):
        opts['ffmpeg_location'] = ffmpeg_loc
        print(f"Using ffmpeg at: {ffmpeg_loc}")
    else:
        if ffmpeg_loc and not (os.path.isdir(ffmpeg_loc) or os.path.isfile(ffmpeg_loc)):
            print(f"Ignoring invalid FFMPEG_LOCATION/FFMPEG_PATH value: {ffmpeg_loc}")
        # Try auto-detect on PATH and set directory so yt-dlp can find ffmpeg
        ff = shutil.which('ffmpeg') or shutil.which('ffmpeg.exe')
        if ff:
            ff_dir = os.path.dirname(ff)
            opts['ffmpeg_location'] = ff_dir
            print(f"Auto-detected ffmpeg in PATH: {ff_dir}")
    try:
        if COOKIES_FILE and os.path.exists(COOKIES_FILE):
            opts['cookiefile'] = COOKIES_FILE
            print(f"Using cookies file: {COOKIES_FILE}")
    except Exception:
        pass

    # Speed-up: use aria2c if available (multi-connection downloader)
    try:
        aria2c_path = os.environ.get('ARIA2C_PATH') or shutil.which('aria2c')
        if aria2c_path:
            opts['external_downloader'] = 'aria2c'
            # Ultra-fast parallelism; tuneable via ARIA2C_THREADS
            threads = max(1, int(os.environ.get('ARIA2C_THREADS', str(ARIA2C_THREADS))))
            opts['external_downloader_args'] = [
                f'--max-connection-per-server={threads}',
                f'--split={threads}',
                '--min-split-size=1M',
                '--enable-http-pipelining=true',
                '--file-allocation=none',
                '--console-log-level=warn'
            ]
            print(f"Using external downloader: aria2c at {aria2c_path} (threads={threads})")
    except Exception:
        pass

    if overrides:
        opts.update(overrides)
    return opts


def ffmpeg_available():
    """Return True only if ffmpeg and ffprobe are actually callable.
    Accept either an absolute folder path containing the binaries, or absolute paths to binaries.
    Ignore placeholder values like 'ffmpeg'.
    """
    loc = os.environ.get('FFMPEG_LOCATION') or os.environ.get('FFMPEG_PATH')

    def bin_exists(p):
        try:
            ok = False
            if p and os.path.isfile(p):
                ok = True
            elif p and os.path.isdir(p):
                # Check folder contains ffmpeg(.exe) and ffprobe(.exe)
                f1 = os.path.join(p, 'ffmpeg.exe')
                f2 = os.path.join(p, 'ffmpeg')
                pr1 = os.path.join(p, 'ffprobe.exe')
                pr2 = os.path.join(p, 'ffprobe')
                ok = (os.path.isfile(f1) or os.path.isfile(f2)) and (os.path.isfile(pr1) or os.path.isfile(pr2))
            return ok
        except Exception:
            return False

    # Validate env-provided location only if it's an absolute file/dir
    if loc and os.path.isabs(loc) and bin_exists(loc):
        return True

    # Fallback to PATH detection
    ff = shutil.which('ffmpeg') or shutil.which('ffmpeg.exe')
    fp = shutil.which('ffprobe') or shutil.which('ffprobe.exe')
    return bool(ff and fp)


def _optimize_video_if_needed(file_path: str) -> str:
    """Optimize video using FFmpeg if size exceeds threshold.
    Returns final file path (optimized or original if skipped/failed).
    """
    try:
        if not AUTO_OPTIMIZE:
            return file_path
        if not os.path.isfile(file_path):
            return file_path
        size_mb = os.path.getsize(file_path) / (1024 * 1024)
        if size_mb <= AUTO_OPTIMIZE_THRESHOLD_MB:
            logger.info(f"[auto-optimize] Skipping optimization, size={size_mb:.1f} MB < threshold={AUTO_OPTIMIZE_THRESHOLD_MB} MB")
            return file_path
        if not ffmpeg_available():
            logger.warning("[auto-optimize] FFmpeg not available; skipping optimization")
            return file_path

        base, ext = os.path.splitext(file_path)
        temp_out = f"{base}.optimized{ext or '.mp4'}"
        # Build FFmpeg command
        ffmpeg_bin = os.environ.get('FFMPEG_PATH') or os.environ.get('FFMPEG_LOCATION') or shutil.which('ffmpeg') or shutil.which('ffmpeg.exe')
        if not ffmpeg_bin:
            logger.warning("[auto-optimize] Could not locate ffmpeg binary; skipping")
            return file_path
        cmd = [
            ffmpeg_bin,
            '-y',
            '-i', file_path,
            '-c:v', 'libx264',
            '-preset', FFMPEG_PRESET,
            '-crf', str(CRF),
            '-c:a', 'aac',
            '-b:a', '128k',
            temp_out
        ]
        logger.info(f"[auto-optimize] Optimizing video: {os.path.basename(file_path)} ({size_mb:.1f} MB) → preset={FFMPEG_PRESET}, crf={CRF}")
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        # If output is smaller, replace original
        if os.path.isfile(temp_out):
            new_size_mb = os.path.getsize(temp_out) / (1024 * 1024)
            logger.info(f"[auto-optimize] Completed: {size_mb:.1f} MB → {new_size_mb:.1f} MB")
            try:
                os.replace(temp_out, file_path)
            except Exception:
                # If replace fails (e.g., permission), fallback to rename original and move
                backup = f"{base}.orig{ext}"
                try:
                    os.replace(file_path, backup)
                    os.replace(temp_out, file_path)
                    try:
                        os.remove(backup)
                    except Exception:
                        pass
                except Exception as rep_err:
                    logger.warning(f"[auto-optimize] Replace failed: {rep_err}")
                    # Keep original if something went wrong
                    try:
                        os.remove(temp_out)
                    except Exception:
                        pass
        return file_path
    except subprocess.CalledProcessError as cpe:
        logger.warning(f"[auto-optimize] FFmpeg failed: {cpe}")
        return file_path
    except Exception as e:
        logger.warning(f"[auto-optimize] Unexpected error: {e}")
        return file_path


def is_valid_youtube_url(url):
    pattern = r'(https?://)?(www\.)?(youtube\.com|youtu\.be)/.+'
    return re.match(pattern, url) is not None

def _simulate_preparing_progress(task_id, duration=3):
    """Simulate preparing progress over specified duration (seconds)"""
    start_time = time.time()
    while time.time() - start_time < duration:
        if task_id not in tasks or tasks[task_id]['status'] != 'preparing':
            break
            
        elapsed = time.time() - start_time
        progress = min((elapsed / duration) * 90, 90)  # Max 90% during preparation
        
        tasks[task_id]['progress'] = f"Preparing download... {progress:.1f}%"
        tasks[task_id]['last_update'] = datetime.now()
        
        time.sleep(0.2)  # Update every 200ms

def _progress_hook(d, task_id):
    if d['status'] == 'downloading':
        tasks[task_id]['status'] = 'downloading'
        tasks[task_id]['last_update'] = datetime.now()
        
        # Calculate percentage from downloaded and total bytes (most accurate)
        if 'downloaded_bytes' in d and 'total_bytes' in d:
            downloaded = d['downloaded_bytes']
            total = d['total_bytes']
            if total > 0:
                percentage = (downloaded / total) * 100
                # Round to 1 decimal place for smooth progression
                progress_text = f"{percentage:.1f}%"
                
                # Add speed and ETA if available
                speed = d.get('speed')
                eta = d.get('eta')
                if speed and speed > 0:
                    speed_mb = speed / (1024 * 1024)  # Convert to MB/s
                    # Estimate total size and human-readable remaining
                    remaining_bytes = max(total - downloaded, 0)
                    remaining_mb = remaining_bytes / (1024 * 1024)
                    progress_text += f" ({speed_mb:.1f} MB/s"
                    if eta and eta > 0:
                        mins, secs = divmod(int(eta), 60)
                        if mins > 0:
                            progress_text += f", {mins}m {secs}s left"
                        else:
                            progress_text += f", {secs}s left"
                    else:
                        # Fallback ETA using remaining / speed
                        if speed > 0:
                            est_eta = int(remaining_bytes / speed)
                            mins, secs = divmod(est_eta, 60)
                            if mins > 0:
                                progress_text += f", {mins}m {secs}s left"
                            else:
                                progress_text += f", {secs}s left"
                    progress_text += ")"
                
                tasks[task_id]['progress'] = progress_text
                tasks[task_id]['eta_seconds'] = int(d.get('eta') or (remaining_bytes / speed if speed else 0) or 0)
                tasks[task_id]['speed_bps'] = int(speed or 0)
                tasks[task_id]['downloaded_bytes'] = int(downloaded)
                tasks[task_id]['total_bytes'] = int(total)
            else:
                tasks[task_id]['progress'] = "0.0%"
        elif 'downloaded_bytes' in d and 'total_bytes_estimate' in d:
            downloaded = d['downloaded_bytes']
            total = d['total_bytes_estimate']
            if total > 0:
                percentage = (downloaded / total) * 100
                # Round to 1 decimal place for smooth progression
                tasks[task_id]['progress'] = f"{percentage:.1f}%"
            else:
                tasks[task_id]['progress'] = "0.0%"
        else:
            # Fallback to parsing _percent_str but clean it up
            percent_str = d.get('_percent_str', '0.0%')
            
            # Remove ANSI escape codes and extra characters
            import re
            clean_percent = re.sub(r'\x1b\[[0-9;]*[mK]', '', percent_str)  # Remove ANSI codes
            clean_percent = re.sub(r'[^\d.%]', '', clean_percent)  # Keep only digits, dots, and %
            if clean_percent and not clean_percent.endswith('%'):
                clean_percent += '%'
            if not clean_percent:
                clean_percent = '0.0%'
            tasks[task_id]['progress'] = clean_percent
            
    elif d['status'] == 'finished':
        tasks[task_id]['last_update'] = datetime.now()
        if tasks[task_id]['status'] != 'processing':
            tasks[task_id]['progress'] = '100%'
    elif d['status'] == 'postprocessing':
        tasks[task_id]['status'] = 'processing'
        tasks[task_id]['progress'] = 'Processing...'
        tasks[task_id]['last_update'] = datetime.now()

def _download(task_id, url, format_selector, ydl_opts):
    try:
        # Immediate feedback - download is starting
        tasks[task_id]['status'] = 'initializing'
        tasks[task_id]['progress'] = 'Connecting to server...'
        tasks[task_id]['last_update'] = datetime.now()
        
        print(f"Starting download for task {task_id}")
        print(f"URL: {url}")
        print(f"Format Selector: {format_selector}")
        print(f"YDL Options: {ydl_opts}")
        
        # Update status to show we're preparing
        tasks[task_id]['status'] = 'preparing'
        tasks[task_id]['progress'] = 'Preparing download... 0.0%'
        tasks[task_id]['last_update'] = datetime.now()
        
        # Start preparing progress simulation in background
        preparing_thread = threading.Thread(target=_simulate_preparing_progress, args=(task_id, 3))
        preparing_thread.daemon = True
        preparing_thread.start()
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Complete preparing progress before starting actual download
            tasks[task_id]['progress'] = 'Preparing download... 100%'
            tasks[task_id]['last_update'] = datetime.now()
            time.sleep(0.5)  # Brief pause to show completion
            
            # Try to download directly
            print("Attempting to download...")
            try:
                info = ydl.extract_info(url, download=True)
            except Exception as primary_err:
                # If aria2c/external downloader fails, retry without it for reliability
                print(f"Primary download failed, retrying without external downloader: {primary_err}")
                safe_opts = ydl_opts.copy()
                safe_opts.pop('external_downloader', None)
                safe_opts.pop('external_downloader_args', None)
                with yt_dlp.YoutubeDL(safe_opts) as ydl_fallback_ed:
                    info = ydl_fallback_ed.extract_info(url, download=True)
            
            # Determine actual output by picking newest file containing video id
            vid = info.get('id')
            actual_filename = None
            newest_mtime = -1
            try:
                for f in os.listdir(DOWNLOAD_FOLDER):
                    if vid and vid in f:
                        p = os.path.join(DOWNLOAD_FOLDER, f)
                        if os.path.isfile(p):
                            mtime = os.path.getmtime(p)
                            if mtime > newest_mtime:
                                newest_mtime = mtime
                                actual_filename = f
            except Exception as scan_err:
                print(f"Error scanning downloads folder: {scan_err}")
            if actual_filename:
                # Optional post-download optimization step
                full_path = os.path.join(DOWNLOAD_FOLDER, actual_filename)
                try:
                    tasks[task_id]['status'] = 'processing'
                    tasks[task_id]['progress'] = 'Optimizing...'
                    tasks[task_id]['last_update'] = datetime.now()
                    optimized_path = _optimize_video_if_needed(full_path)
                    # Ensure filename reflects the final file (path may be same)
                    final_name = os.path.basename(optimized_path)
                    tasks[task_id]['status'] = 'finished'
                    tasks[task_id]['filename'] = final_name
                except Exception as opt_err:
                    logger.warning(f"[auto-optimize] Error during optimization: {opt_err}")
                    tasks[task_id]['status'] = 'finished'
                    tasks[task_id]['filename'] = actual_filename
                print(f"Download completed successfully: {tasks[task_id]['filename']}")
            else:
                raise Exception("Download finished but file not found. Check ffmpeg or write permissions.")
            
    except yt_dlp.DownloadError as e:
        error_msg = str(e)
        print(f"yt-dlp Download error for task {task_id}: {error_msg}")
        
        # Enhanced fallback strategies for 2025 YouTube issues
        if any(keyword in error_msg.lower() for keyword in ["requested format is not available", "403", "forbidden", "unavailable", "private", "blocked"]):
            print("Attempting enhanced fallback downloads...")
            
            # Comprehensive fallback strategies with different clients and formats
            fallback_strategies = [
                # Strategy 1: Try different clients with original format
                {'client': 'android_creator', 'format': format_selector, 'desc': 'Android Creator client'},
                {'client': 'android_music', 'format': format_selector, 'desc': 'Android Music client'},
                {'client': 'web', 'format': format_selector, 'desc': 'Web client'},
                
                # Strategy 2: Safe MP4 formats with different clients
                {'client': 'android', 'format': 'best[ext=mp4][height<=720]', 'desc': '720p MP4 (Android)'},
                {'client': 'web', 'format': 'best[ext=mp4][height<=480]', 'desc': '480p MP4 (Web)'},
                {'client': 'ios', 'format': 'best[ext=mp4][height<=360]', 'desc': '360p MP4 (iOS)'},
                
                # Strategy 3: Progressive formats (video+audio combined)
                {'client': 'android', 'format': '18', 'desc': '360p MP4 progressive'},
                {'client': 'web', 'format': '22', 'desc': '720p MP4 progressive'},
                {'client': 'android', 'format': '136+140', 'desc': '720p video + audio'},
                
                # Strategy 4: Audio-only fallback
                {'client': 'android', 'format': 'bestaudio[ext=m4a]', 'desc': 'Best audio M4A'},
                {'client': 'web', 'format': 'bestaudio', 'desc': 'Best audio any format'},
                
                # Strategy 5: Last resort - any available format
                {'client': 'android', 'format': 'worst', 'desc': 'Lowest quality available'},
                {'client': 'web', 'format': 'best', 'desc': 'Best available (any)'},
            ]
            
            for strategy in fallback_strategies:
                try:
                    print(f"Trying fallback: {strategy['desc']}")
                    fallback_opts = ydl_opts.copy()
                    fallback_opts['format'] = strategy['format']
                    
                    # Update client in extractor args
                    fallback_opts.setdefault('extractor_args', {}).setdefault('youtube', {})['player_client'] = strategy['client']
                    
                    # Add extra safety measures
                    fallback_opts.update({
                        'ignoreerrors': True,
                        'no_warnings': True,
                        'extract_flat': False,
                        'writesubtitles': False,
                        'writeautomaticsub': False,
                        'sleep_interval': 3,  # More conservative
                        'retries': 3,
                    })
                    
                    with yt_dlp.YoutubeDL(fallback_opts) as ydl_fallback:
                        info = ydl_fallback.extract_info(url, download=True)
                        
                        # Find the downloaded file
                        vid = info.get('id')
                        actual_filename = None
                        newest_mtime = -1
                        try:
                            for f in os.listdir(DOWNLOAD_FOLDER):
                                if vid and vid in f:
                                    p = os.path.join(DOWNLOAD_FOLDER, f)
                                    if os.path.isfile(p):
                                        mtime = os.path.getmtime(p)
                                        if mtime > newest_mtime:
                                            newest_mtime = mtime
                                            actual_filename = f
                        except Exception as scan_err:
                            print(f"Error scanning downloads folder: {scan_err}")
                        
                        if actual_filename:
                            tasks[task_id]['status'] = 'finished'
                            tasks[task_id]['filename'] = actual_filename
                            print(f"Fallback download completed with {strategy['desc']}: {actual_filename}")
                            return
                        else:
                            print(f"Fallback {strategy['desc']} completed but file not found")
                        
                except Exception as fallback_error:
                    print(f"Fallback {strategy['desc']} failed: {fallback_error}")
                    continue
            
            print("All enhanced fallback attempts failed")
        
        tasks[task_id]['status'] = 'error'
        tasks[task_id]['error'] = error_msg
        
    except Exception as e:
        print(f"General download error for task {task_id}: {str(e)}")
        tasks[task_id]['status'] = 'error'
        tasks[task_id]['error'] = str(e)
    finally:
        # If stuck in processing for a long time (> 2 minutes), surface a clearer hint
        task = tasks.get(task_id, {})
        if task.get('status') == 'processing':
            task['progress'] = task.get('progress', '') + ' (merging... ensure FFMPEG_LOCATION is set)'
        logger.info(f"Task {task_id} finished with status={tasks.get(task_id,{}).get('status')} at {datetime.now().isoformat()}")

@app.route('/api/video_info', methods=['POST'])
def api_video_info():
    data = request.get_json()
    url = data.get('url') if data else None
    if not url or not is_valid_youtube_url(url):
        return jsonify({'error': 'Invalid or missing YouTube URL.'}), 400
    
    try:
        # Check cache first for speed
        cached_result = get_cached_formats(url)
        if cached_result:
            return jsonify(cached_result)
        
        # Single client approach for maximum speed
        try:
            # Fast path: single client for speed when PREFER_SPEED is enabled
            player_clients = ['android'] if PREFER_SPEED else ['android', 'web']
            ydl_opts = build_ydl_opts({
                'skip_download': True,
                'extractor_args': {'youtube': {'player_client': player_clients}},
                'http_headers': {'Referer': url, 'Origin': 'https://www.youtube.com'}
            })
            logger.info(f"Fetching video info for URL: {url} (clients={player_clients})")
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
            logger.info(f"Success: title='{info.get('title')}', id='{info.get('id')}', formats={len(info.get('formats', []))}")
            
        except Exception as e:
            last_error = str(e)
            logger.error(f"Video info extraction failed: {last_error}")
            info = None
        if not info:
            # Provide clearer feedback for anti-bot wall
            msg = 'YouTube requires sign-in or verification. Please add cookies to continue.'
            if last_error:
                msg += f' Details: {last_error}'
            logger.error(f"/api_video_info failed: {msg}")
            return jsonify({'error': msg}), 403

        formats = []
        print(f"Processing formats for video: {info.get('title')}")
        
        # Scan all formats to ensure we include higher qualities
        source_formats = info.get('formats', [])
        seen_keys = set()
        
        for f in source_formats:
            # Filtering using pre-compiled regex
            protocol = f.get('protocol', '')
            format_note = f.get('format_note', '')
            
            if (HLS_PATTERN.search(protocol) or 
                PREMIUM_PATTERN.search(format_note)):
                continue
            
            height = f.get('height') or 0
            if height <= 0:  # Skip audio-only formats for speed
                continue
                
            fps = f.get('fps') or 0
            ext = f.get('ext') or 'mp4'
            
            # Ultra-fast deduplication
            key = f"{height}_{fps}_{ext}"
            if key in seen_keys:
                continue
            seen_keys.add(key)
            
            # Minimal filesize calculation
            filesize = f.get('filesize') or f.get('filesize_approx')
            filesize_mb = round(filesize / 1048576, 1) if filesize and filesize > 0 else None
            
            resolution_str = f"{f.get('width', 0)}x{height}" if height > 0 else None
            
            # Determine progressive capability and expose direct URL for progressive streams
            has_video = (f.get('vcodec') and f.get('vcodec') != 'none')
            has_audio = (f.get('acodec') and f.get('acodec') != 'none')
            is_progressive = bool(has_video and has_audio and not HLS_PATTERN.search(protocol))
            direct_url = f.get('url') if is_progressive else None

            formats.append({
                'format_id': f.get('format_id'),
                'ext': ext,
                'quality': f.get('format_note', f"{height}p"),
                'filesize': filesize,
                'filesize_mb': filesize_mb,
                'resolution': resolution_str,
                'fps': fps,
                'tbr': f.get('tbr'),
                'format_note': f.get('format_note'),
                'height': height,
                'vcodec': f.get('vcodec'),
                'acodec': f.get('acodec'),
                'is_progressive': is_progressive,
                'direct_url': direct_url,
                'mime_type': f.get('mime_type'),
                'protocol': f.get('protocol')
            })
            
            # No limit: include all heights to offer high-quality options
        
        print(f"Total usable formats found: {len(formats)}")

        # Format duration from seconds to readable format
        duration_seconds = info.get('duration')
        duration_formatted = 'N/A'
        if duration_seconds:
            hours = duration_seconds // 3600
            minutes = (duration_seconds % 3600) // 60
            seconds = duration_seconds % 60
            if hours > 0:
                duration_formatted = f"{hours}:{minutes:02d}:{seconds:02d}"
            else:
                duration_formatted = f"{minutes}:{seconds:02d}"
        
        # Format upload date
        upload_date = info.get('upload_date')
        upload_date_formatted = 'N/A'
        if upload_date:
            try:
                date_obj = datetime.strptime(upload_date, '%Y%m%d')
                upload_date_formatted = date_obj.strftime('%B %d, %Y')
            except:
                upload_date_formatted = upload_date

        result = {
            'title': info.get('title'),
            'thumbnail': info.get('thumbnail'),
            'duration': duration_formatted,
            'duration_seconds': duration_seconds,
            'view_count': info.get('view_count'),
            'upload_date': upload_date_formatted,
            'uploader': info.get('uploader') or info.get('channel'),
            'url': url,
            'formats': formats
        }
        
        # Cache the result for future requests
        cache_formats(url, result)
        
        return jsonify(result)
    except Exception as e:
        logger.exception(f"/api_video_info error for URL={url}: {e}")
        return jsonify({'error': 'Server error while fetching video details.'}), 500

@app.route('/api/download', methods=['POST'])
def api_download():
    data = request.get_json()
    url = data.get('url')
    format_id = data.get('format_id')
    if not url or not is_valid_youtube_url(url):
        return jsonify({'error': 'Invalid or missing YouTube URL.'}), 400

    task_id = str(uuid.uuid4())
    
    def progress_hook(d):
        _progress_hook(d, task_id)

    # Track if the user chose an audio-only stream
    audio_only_selected = False

    # Handle format selection with comprehensive validation
    print(f"Requested format_id: {format_id}")
    
    # Discovery: prefer a single fast client when PREFER_SPEED is enabled
    discovery = []
    clients_for_discovery = ['android'] if PREFER_SPEED else ['android', 'ios', 'web', 'web_creator', 'tv_embedded']
    
    for client in clients_for_discovery:
        try:
            ydl_opts_check = build_ydl_opts({'skip_download': True})
            ydl_opts_check.setdefault('extractor_args', {}).setdefault('youtube', {})['player_client'] = client
            
            # Client-specific optimizations for discovery
            if client.startswith('android'):
                ydl_opts_check['extractor_args']['youtube']['skip'] = ['hls', 'dash']
            elif client == 'web':
                ydl_opts_check['extractor_args']['youtube']['skip'] = ['hls']
            
            with yt_dlp.YoutubeDL(ydl_opts_check) as ydl:
                info_cli = ydl.extract_info(url, download=False)
            discovery.append((client, info_cli))
            print(f"Discovery successful with client {client}: {len(info_cli.get('formats', []))} formats found")
            # Speed mode: break after first success
            if PREFER_SPEED:
                break
        except yt_dlp.DownloadError as e:
            print(f"Discovery with client {client} failed: {e}")
            continue
        except Exception as e:
            print(f"Unexpected discovery error with client {client}: {e}")
            continue
    
    if not discovery:
        return jsonify({'error': 'Failed to fetch formats from YouTube. The video may be private, geo-blocked, or require authentication.'}), 502

    def find_format_in_discovery(fmt_id):
        for client, info_cli in discovery:
            for f in info_cli.get('formats', []):
                if f.get('format_id') == fmt_id:
                    return client, f, info_cli
        return None, None, None

    # Decide selector and client
    chosen_client = 'web'
    if format_id == 'best':
        # Prefer MP4/H.264 when possible, then fallback to any best
        # Prefer fast/quality mix; yt-dlp will pick best under cap
        format_selector = (
            'bestvideo[height<=4320]+bestaudio/best'
        )
        # Ensure chosen client has separate video streams
        has_video_only = False
        for client, info_cli in discovery:
            if any((f.get('vcodec') and f.get('vcodec') != 'none') and (not f.get('acodec') or f.get('acodec') == 'none') for f in info_cli.get('formats', [])):
                chosen_client = client
                has_video_only = True
                break
        if not has_video_only:
            # Fall back to any client; yt-dlp will pick 'best'
            chosen_client = discovery[0][0]
        # For best, try to prefer AV1/VP9 high-res when merging is available
        # This leaves room for yt-dlp to pick the highest quality
        format_selector = (
            'bestvideo[height<=4320]+bestaudio/best'
        )
        print(f"Using client {chosen_client} for 'best' (quality-first)")
    else:
        # Specific format requested
        client_for_fmt, requested_format, info_for_fmt = find_format_in_discovery(format_id)
        if requested_format:
            chosen_client = client_for_fmt
            has_video = requested_format.get('vcodec') and requested_format.get('vcodec') != 'none'
            has_audio = requested_format.get('acodec') and requested_format.get('acodec') != 'none'
            if has_video and not has_audio:
                # video-only: merge with best audio
                # Prefer m4a to keep MP4 compatibility; fallback to bestaudio if missing
                format_selector = f"{format_id}+bestaudio[ext=m4a]/{format_id}+bestaudio"
            elif (not has_video) and has_audio:
                # audio-only: download as-is
                format_selector = format_id
                audio_only_selected = True
            else:
                # progressive (both)
                format_selector = format_id
            print(f"Using client {chosen_client} for requested format {format_id}")
        else:
            # Not found; allow selector strings from frontend or fallback to MP4-preferred best
            if isinstance(format_id, str) and ('bestvideo' in format_id or 'best' in format_id or '+' in format_id or '[' in format_id):
                format_selector = format_id
            else:
                format_selector = 'bestvideo[ext=mp4][vcodec^=avc1][height<=4320]+bestaudio[ext=m4a]/best[ext=mp4]/best'
            chosen_client = discovery[0][0]
            print(f"Requested format {format_id} not found; using selector: {format_selector} with client {chosen_client}")

    # Build download options with selected client
    # Unique output to avoid reusing small existing files
    outtmpl = os.path.join(DOWNLOAD_FOLDER, '%(title).50s_%(id)s_%(format_id)s.%(ext)s')
    
    ydl_opts = build_ydl_opts({
        'outtmpl': outtmpl,
        'progress_hooks': [progress_hook],
        'postprocessor_hooks': [progress_hook],
        'format': format_selector,
        'ignoreerrors': False,
        'extract_flat': False,
        # Prefer MKV when high-quality codecs (VP9/AV1/webm) are involved to avoid quality loss; otherwise MP4
        'merge_output_format': 'mp4',
        'writesubtitles': False,
        'writeautomaticsub': False,
        'overwrites': True,  # Ensure we don't keep an old low-quality file
        # Performance optimizations
        'socket_timeout': 10,
        'retries': 2,
        'fragment_retries': 2,
        'skip_unavailable_fragments': True,
        'concurrent_fragment_downloads': 4,
    })
    # If user picked pure audio, avoid forcing merge container
    if audio_only_selected:
        ydl_opts.pop('merge_output_format', None)
    else:
        if not ffmpeg_available():
            # No ffmpeg: force progressive-only fallback (no merging)
            # Try to respect requested height if present; otherwise cap at 720p
            import re as _re
            m = _re.search(r'height\s*=\s*(\d+)', str(format_selector) or '')
            if m:
                h = int(m.group(1))
            else:
                h = 720
            # Progressive formats have both audio and video codecs
            ydl_opts['format'] = f"best[acodec!=none][vcodec!=none][height<=%d]/best[acodec!=none][vcodec!=none]" % h
            ydl_opts.pop('merge_output_format', None)
        else:
            # If the selector hints webm/opus or AV1, prefer MKV to avoid mp4 merge failures
            selector_lc = (format_selector or '').lower()
            if any(tok in selector_lc for tok in ['webm', 'opus', 'av01', 'vp9', 'vp09']):
                ydl_opts['merge_output_format'] = 'mkv'
    ydl_opts.setdefault('extractor_args', {}).setdefault('youtube', {})['player_client'] = chosen_client
    # Ensure Referer/Origin headers point to the video URL to reduce 403s
    ydl_opts.setdefault('http_headers', {})['Referer'] = url
    ydl_opts.setdefault('http_headers', {})['Origin'] = 'https://www.youtube.com'
    
    print(f"Download request - URL: {url}, Format: {format_selector}, Client: {chosen_client}")

    tasks[task_id] = {'status': 'starting', 'progress': '0%', 'last_update': datetime.now()}
    
    thread = threading.Thread(target=_download, args=(task_id, url, format_selector, ydl_opts))
    thread.start()

    return jsonify({'task_id': task_id})

@app.route('/api/progress/<task_id>')
def api_progress(task_id):
    task = tasks.get(task_id, {})
    return jsonify(task)

@app.route('/api/progress-stream/<task_id>')
def api_progress_stream(task_id):
    """Server-Sent Events stream for real-time progress updates"""
    def event_stream():
        last_sent = None
        # Send initial event quickly even if task not found yet
        while True:
            task = tasks.get(task_id, {})
            payload = {
                'status': task.get('status'),
                'progress': task.get('progress'),
                'eta_seconds': task.get('eta_seconds'),
                'filename': task.get('filename'),
                'error': task.get('error')
            }
            data = json.dumps(payload, ensure_ascii=False)
            if data != last_sent:
                yield f"data: {data}\n\n"
                last_sent = data
            # Stop streaming after terminal state
            if payload.get('status') in ('finished', 'error'):
                break
            time.sleep(0.5)
    headers = {
        'Cache-Control': 'no-cache',
        'X-Accel-Buffering': 'no'  # Disable buffering on some proxies
    }
    return Response(stream_with_context(event_stream()), mimetype='text/event-stream', headers=headers)

@app.route('/')
def home():
    # Redirect root to the universal downloader
    return redirect(url_for('universal'))

@app.route('/universal')
def universal():
    return render_template('universal.html')

@app.route('/static/sw.js')
def service_worker():
    return send_file('static/sw.js', mimetype='application/javascript')

@app.route('/static/manifest.json')
def manifest():
    return send_file('static/manifest.json', mimetype='application/json')



# Universal Downloader API Endpoints
@app.route('/api/<platform>/analyze', methods=['POST'])
def analyze_media(platform):
    """Analyze media from different platforms"""
    try:
        data = request.get_json()
        url = data.get('url')
        
        if not url:
            return jsonify({'error': 'URL is required'}), 400
        
        # Log request
        logger.info(f"Analyze request platform={platform}, url={url}")
        
        # Route to appropriate platform handler
        if platform == 'youtube':
            return analyze_youtube(url)
        elif platform == 'instagram':
            return analyze_instagram(url)
        elif platform == 'facebook':
            return analyze_facebook(url)
        elif platform == 'tiktok':
            return analyze_tiktok(url)
        elif platform == 'twitter':
            return analyze_twitter(url)
        elif platform == 'pinterest':
            return analyze_pinterest(url)
        else:
            return jsonify({'error': f'Platform {platform} not supported yet'}), 400
            
    except Exception as e:
        logger.error(f"Error analyzing {platform} media: {str(e)}")
        return jsonify({'error': 'Failed to analyze media'}), 500

def analyze_youtube(url):
    """Analyze YouTube video - optimized single client approach"""
    try:
        # Check cache first for speed
        cached_result = get_cached_formats(url)
        if cached_result:
            return jsonify(cached_result)
        
        # Single client approach for maximum speed
        try:
            clients = ['web', 'android', 'ios', 'web_creator', 'tv_embedded']
            info = None
            best_client = None
            best_count = -1
            last_error = None
            logger.info(f"[universal] Fetching video info for URL: {url}")
            for client in clients:
                try:
                    ydl_opts = build_ydl_opts({
                        'skip_download': True,
                        'extractor_args': {'youtube': {'player_client': client}},
                        'http_headers': {'Referer': url, 'Origin': 'https://www.youtube.com'}
                    })
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info_try = ydl.extract_info(url, download=False)
                    # Count usable formats (video with height and not HLS/premium)
                    sf = info_try.get('formats', []) or []
                    usable = 0
                    for f in sf:
                        proto = (f.get('protocol') or '')
                        note = (f.get('format_note') or '')
                        if (HLS_PATTERN.search(proto) or PREMIUM_PATTERN.search(note)):
                            continue
                        if (f.get('height') or 0) > 0:
                            usable += 1
                    logger.info(f"[universal] Client '{client}' yielded total={len(sf)} usable={usable}")
                    if usable > best_count:
                        best_count = usable
                        info = info_try
                        best_client = client
                except Exception as ce:
                    last_error = str(ce)
                    logger.warning(f"[universal] Client '{client}' failed: {last_error}")
                    continue
            if not info:
                raise Exception(last_error or 'Failed to extract formats from all clients')
            logger.info(f"[universal] Success via client='{best_client}': title='{info.get('title')}', id='{info.get('id')}', formats={len(info.get('formats', []))}")
            
        except Exception as e:
            last_error = str(e)
            logger.error(f"[universal] Video info extraction failed: {last_error}")
            info = None
        if not info:
            msg = 'YouTube requires sign-in or verification. Please add cookies to continue.'
            if last_error:
                msg += f' Details: {last_error}'
            logger.error(f"[universal] analyze_youtube failed: {msg}")
            return jsonify({'error': msg}), 403
        # Ultra-fast format processing (same as main API)
        formats = []
        logger.info(f"[universal] Processing formats for video: {info.get('title')}")
        
        source_formats = info.get('formats', [])
        seen_keys = set()
        
        # Scan all formats to ensure we include higher qualities
        for f in source_formats:
            # Filtering using pre-compiled regex
            protocol = f.get('protocol', '')
            format_note = f.get('format_note', '')
            
            if (HLS_PATTERN.search(protocol) or 
                PREMIUM_PATTERN.search(format_note)):
                continue
            
            height = f.get('height') or 0
            if height <= 0:  # Skip audio-only formats for speed
                continue
                
            fps = f.get('fps') or 0
            ext = f.get('ext') or 'mp4'
            
            # Ultra-fast deduplication
            key = f"{height}_{fps}_{ext}"
            if key in seen_keys:
                continue
            seen_keys.add(key)
            
            # Minimal filesize calculation
            filesize = f.get('filesize') or f.get('filesize_approx')
            filesize_mb = round(filesize / 1048576, 1) if filesize and filesize > 0 else None
            
            resolution_str = f"{f.get('width', 0)}x{height}" if height > 0 else None
            
            # Determine progressive capability and expose direct URL for progressive streams
            has_video = (f.get('vcodec') and f.get('vcodec') != 'none')
            has_audio = (f.get('acodec') and f.get('acodec') != 'none')
            is_progressive = bool(has_video and has_audio and not HLS_PATTERN.search(protocol))
            direct_url = f.get('url') if is_progressive else None

            formats.append({
                'format_id': f.get('format_id'),
                'ext': ext,
                'quality': f.get('format_note', f"{height}p"),
                'filesize': filesize,
                'filesize_mb': filesize_mb,
                'resolution': resolution_str,
                'fps': fps,
                'tbr': f.get('tbr'),
                'format_note': f.get('format_note'),
                'height': height,
                'vcodec': f.get('vcodec'),
                'acodec': f.get('acodec'),
                'is_progressive': is_progressive,
                'direct_url': direct_url,
                'mime_type': f.get('mime_type'),
                'protocol': f.get('protocol')
            })
            
            # No limit: include all heights to offer high-quality options
        
        logger.info(f"[universal] Total usable formats found: {len(formats)}")

        # Format duration from seconds to readable format
        duration_seconds = info.get('duration')
        duration_formatted = 'N/A'
        if duration_seconds:
            hours = duration_seconds // 3600
            minutes = (duration_seconds % 3600) // 60
            seconds = duration_seconds % 60
            if hours > 0:
                duration_formatted = f"{hours}:{minutes:02d}:{seconds:02d}"
            else:
                duration_formatted = f"{minutes}:{seconds:02d}"

        result = {
            'title': info.get('title', 'Unknown Title'),
            'thumbnail': info.get('thumbnail', ''),
            'duration': duration_formatted,
            'views': info.get('view_count', 0),
            'date': info.get('upload_date', 'Unknown'),
            'author': info.get('uploader', 'Unknown'),
            'formats': formats
        }
        
        # Cache the result
        cache_formats(url, result)
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error analyzing YouTube video: {str(e)}")
        return jsonify({'error': 'Failed to analyze YouTube video'}), 500

def analyze_instagram(url):
    """Analyze Instagram media - placeholder for future implementation"""
    return jsonify({
        'error': 'Instagram downloader coming soon! 🚧',
        'message': 'We are working on Instagram support. Stay tuned!'
    }), 501

@app.route('/api/upload_cookies', methods=['POST'])
def upload_cookies():
    """Accepts a text/plain or multipart file upload named 'cookies' and saves to cookies.txt"""
    try:
        if 'cookies' in request.files:
            f = request.files['cookies']
            content = f.read()
        else:
            # Fallback to raw body
            content = request.data or b''
        if not content:
            return jsonify({'error': 'No cookies provided'}), 400
        # Save to default cookies path
        with open(COOKIES_FILE, 'wb') as fh:
            fh.write(content)
        return jsonify({'message': 'Cookies uploaded', 'path': COOKIES_FILE})
    except Exception as e:
        logger.exception(f"Failed to upload cookies: {e}")
        return jsonify({'error': 'Failed to upload cookies'}), 500

def analyze_facebook(url):
    """Analyze Facebook media - placeholder for future implementation"""
    return jsonify({
        'error': 'Facebook downloader coming soon! 🚧',
        'message': 'We are working on Facebook support. Stay tuned!'
    }), 501

def analyze_tiktok(url):
    """Analyze TikTok media - placeholder for future implementation"""
    return jsonify({
        'error': 'TikTok downloader coming soon! 🚧',
        'message': 'We are working on TikTok support. Stay tuned!'
    }), 501

def analyze_twitter(url):
    """Analyze Twitter media - placeholder for future implementation"""
    return jsonify({
        'error': 'Twitter downloader coming soon! 🚧',
        'message': 'We are working on Twitter support. Stay tuned!'
    }), 501

def analyze_pinterest(url):
    """Analyze Pinterest media - placeholder for future implementation"""
    return jsonify({
        'error': 'Pinterest downloader coming soon! 🚧',
        'message': 'We are working on Pinterest support. Stay tuned!'
    }), 501

def format_duration(seconds):
    """Format duration in seconds to readable format"""
    if not seconds:
        return 'Unknown'
    
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    
    if hours > 0:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    else:
        return f"{minutes}:{seconds:02d}"

def format_number(num):
    """Format large numbers with K, M, B suffixes"""
    if not num:
        return 'Unknown'
    
    if num >= 1_000_000_000:
        return f"{num / 1_000_000_000:.1f}B"
    elif num >= 1_000_000:
        return f"{num / 1_000_000:.1f}M"
    elif num >= 1_000:
        return f"{num / 1_000:.1f}K"
    else:
        return str(num)

def _best_video_per_height(source_formats):
    """Pick the best video-only format per height, preferring AVC(H.264) and MP4/WebM order by bitrate, fps."""
    best_by_h = {}
    for f in source_formats:
        height = f.get('height') or 0
        vcodec = (f.get('vcodec') or '').lower()
        acodec = (f.get('acodec') or '').lower()
        if height <= 0:  # skip audio-only
            continue
        # prefer video-only; but allow muxed if it exists and is MP4
        is_video_only = (acodec in ('', 'none', None))
        score = 0
        if vcodec.startswith('avc') or 'h264' in vcodec:
            score += 1000
        score += (f.get('tbr') or 0)  # bitrate preference
        score += (f.get('fps') or 0) * 2
        # Small boost if container is mp4
        if (f.get('ext') or '').lower() == 'mp4':
            score += 50
        cur = best_by_h.get(height)
        if not cur or score > cur['__score']:
            g = dict(f)
            g['__score'] = score
            best_by_h[height] = g
    return [best_by_h[h] for h in sorted(best_by_h.keys(), reverse=True)]

def process_formats(formats):
    """Process formats for universal interface (prefer best per height)."""
    # Prefer the best video stream per height to show clear high-quality choices
    selected = _best_video_per_height(formats)
    processed = []
    for fmt in selected:
        filesize = fmt.get('filesize') or fmt.get('filesize_approx')
        filesize_mb = None
        if filesize and filesize > 0:
            filesize_mb = filesize / (1024 * 1024)
        processed.append({
            'format_id': fmt.get('format_id'),
            'ext': fmt.get('ext', 'mp4'),
            'quality': fmt.get('format_note') or (f"{fmt.get('height')}p" if fmt.get('height') else 'Unknown'),
            'resolution': fmt.get('resolution') or (f"{fmt.get('width','?')}x{fmt.get('height','?')}") ,
            'filesize_mb': filesize_mb,
            'vcodec': fmt.get('vcodec'),
            'acodec': fmt.get('acodec'),
            'fps': fmt.get('fps'),
            'tbr': fmt.get('tbr'),
            'height': fmt.get('height')
        })
    return processed

@app.route('/api/<platform>/download', methods=['POST'])
def download_media(platform):
    """Download media from different platforms"""
    try:
        data = request.get_json()
        url = data.get('url')
        format_id = data.get('format_id')
        
        if not url or not format_id:
            return jsonify({'error': 'URL and format_id are required'}), 400
        
        # Route to appropriate platform downloader
        if platform == 'youtube':
            return download_youtube_universal(url, format_id)
        elif platform == 'instagram':
            return jsonify({'error': 'Instagram downloader coming soon! 🚧'}), 501
        elif platform == 'facebook':
            return jsonify({'error': 'Facebook downloader coming soon! 🚧'}), 501
        elif platform == 'tiktok':
            return jsonify({'error': 'TikTok downloader coming soon! 🚧'}), 501
        elif platform == 'twitter':
            return jsonify({'error': 'Twitter downloader coming soon! 🚧'}), 501
        elif platform == 'pinterest':
            return jsonify({'error': 'Pinterest downloader coming soon! 🚧'}), 501
        else:
            return jsonify({'error': f'Platform {platform} not supported yet'}), 400
            
    except Exception as e:
        logger.error(f"Error downloading {platform} media: {str(e)}")
        return jsonify({'error': 'Failed to download media'}), 500

def download_youtube_universal(url, requested_format_id):
    """Download YouTube video for universal interface - optimized single approach."""
    
    # Use the same optimized approach as the main download function
    task_id = str(uuid.uuid4())
    
    # Determine format selector with strong MP4 preference
    format_selector = requested_format_id
    if requested_format_id == 'best':
        # Prefer highest quality video+audio (any codec) then fall back to progressive MP4
        # This ensures VP9/AV1 high-res streams are used when AVC is unavailable
        format_selector = (
            'bestvideo*[height<=4320]+bestaudio/bestvideo*[height<=2160]+bestaudio/'
            'bestvideo*[height<=1440]+bestaudio/bestvideo*[height<=1080]+bestaudio/'
            '22/18/best[ext=mp4][height<=1080]'
        )
    elif requested_format_id and '+' not in requested_format_id:
        # For single video-only ids, merge with best AAC/M4A audio if possible
        format_selector = (
            f"{requested_format_id}+bestaudio[ext=m4a]/"
            f"{requested_format_id}+bestaudio/"
            f"{requested_format_id}"
        )

    # Pick best client for download (matches analysis strategy)
    clients = ['web', 'android', 'ios', 'web_creator', 'tv_embedded']
    best_client = None
    best_count = -1
    for client in clients:
        try:
            probe_opts = build_ydl_opts({
                'skip_download': True,
                'extractor_args': {'youtube': {'player_client': client}},
                'http_headers': {'Referer': url, 'Origin': 'https://www.youtube.com'}
            })
            with yt_dlp.YoutubeDL(probe_opts) as ydl_probe:
                info_try = ydl_probe.extract_info(url, download=False)
            sf = info_try.get('formats', []) or []
            usable = 0
            for f in sf:
                proto = (f.get('protocol') or '')
                note = (f.get('format_note') or '')
                if (HLS_PATTERN.search(proto) or PREMIUM_PATTERN.search(note)):
                    continue
                if (f.get('height') or 0) > 0:
                    usable += 1
            if usable > best_count:
                best_count = usable
                best_client = client
        except Exception:
            continue
    if not best_client:
        best_client = 'web'
    logger.info(f"[universal_dl] Selected client '{best_client}' for download. URL: {url}")

    # Build optimized yt-dlp options with chosen client
    ydl_opts = build_ydl_opts({
        'format': format_selector,
        'outtmpl': os.path.join(DOWNLOAD_FOLDER, '%(title)s [%(id)s].%(ext)s'),
        'progress_hooks': [lambda d: _progress_hook(d, task_id)],
        'prefer_free_formats': False,
        'extractor_args': {'youtube': {'player_client': best_client}},
        'http_headers': {'Referer': url, 'Origin': 'https://www.youtube.com'}
    })

    # If ffmpeg is not available, ensure we only pick progressive MP4 to avoid merging
    if not ffmpeg_available():
        ydl_opts['format'] = (
            '22/18/best[ext=mp4][acodec!=none][vcodec!=none][height<=1080]/'
            'best[acodec!=none][vcodec!=none][height<=1080]'
        )
        logger.warning(f"[universal_dl] ffmpeg not available; forcing progressive fallback format='{ydl_opts['format']}'")
    else:
        # Merge/remux to MP4 when possible (avoid re-encoding to preserve quality)
        # If codecs are not MP4-friendly, allow MKV to avoid re-encode and keep quality
        ydl_opts['merge_output_format'] = 'mp4'
        ydl_opts['postprocessors'] = [
            { 'key': 'FFmpegVideoRemuxer', 'preferedformat': 'mp4' }
        ]
        ydl_opts['allow_multiple_video_streams'] = False
        ydl_opts['allow_unplayable_formats'] = False
        logger.info("[universal_dl] ffmpeg available; will remux to mp4 or keep MKV to preserve quality")
        # If merging to MP4 fails due to codecs, yt-dlp will keep original container (often MKV) to preserve quality

    logger.info(f"[universal_dl] Starting download with final format='{ydl_opts['format']}' and client='{best_client}'")
    
    # Initialize task
    tasks[task_id] = {
        'status': 'initializing',
        'progress': 'Starting download...',
        'last_update': datetime.now()
    }
    
    # Start download in background thread
    download_thread = threading.Thread(
        target=_download,
        args=(task_id, url, format_selector, ydl_opts)
    )
    download_thread.daemon = True
    download_thread.start()
    
    logger.info(f"[universal] Download task {task_id} started for URL: {url}")
    
    return jsonify({
        'task_id': task_id,
        'message': 'Download started successfully',
        'format': requested_format_id,
        'filename': tasks.get(task_id, {}).get('filename') if tasks.get(task_id, {}).get('status') == 'finished' else None
    })

@app.route('/download/<path:filename>')
def download_file(filename):
    """Serve a file from the downloads directory safely with correct headers.
    Supports unicode filenames and spaces via URL-encoding on the client.
    """
    try:
        # Flask safely serves from a directory and prevents traversal
        return send_from_directory(
            DOWNLOAD_FOLDER,
            filename,
            as_attachment=True,
            download_name=filename  # hint the original filename for save dialog
        )
    except (FileNotFoundError, NotFound):
        return jsonify({'error': 'File not found.'}), 404
    except Exception as e:
        logger.exception(f"Error serving download for '{filename}': {e}")
        return jsonify({'error': 'Unable to serve file.'}), 500

@app.route('/api/debug_formats/<video_id>')
def debug_formats(video_id):
    """Debug endpoint to see all available formats for a video"""
    try:
        url = f"https://www.youtube.com/watch?v={video_id}"
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
        }
        
        def extract_with_retry():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(url, download=False)
        
        info = network_retry_wrapper(extract_with_retry, max_retries=3, delay=2)
        if info is None:
            raise Exception("Failed to extract video info after retries")
            
        formats_debug = []
        for f in info.get('formats', []):
            formats_debug.append({
                'format_id': f.get('format_id'),
                'ext': f.get('ext'),
                'resolution': f.get('resolution'),
                'height': f.get('height'),
                'width': f.get('width'),
                'vcodec': f.get('vcodec'),
                'acodec': f.get('acodec'),
                'filesize': f.get('filesize'),
                'tbr': f.get('tbr'),
                'fps': f.get('fps'),
                'format_note': f.get('format_note'),
                'quality': f.get('quality'),
            })
        
        return jsonify({
            'title': info.get('title'),
            'formats': formats_debug,
            'total_formats': len(formats_debug)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/clear_downloads')
def clear_downloads():
    try:
        for f in os.listdir(DOWNLOAD_FOLDER):
            os.remove(os.path.join(DOWNLOAD_FOLDER, f))
        return jsonify({'message': 'All downloaded files have been cleared.'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health')
def health_check():
    """Health check endpoint for monitoring"""
    try:
        # Test basic functionality
        import socket
        socket.create_connection(('8.8.8.8', 53), timeout=5).close()
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'version': 'enhanced-2025',
            'network': 'ok',
            'tasks_active': len(tasks)
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'timestamp': datetime.now().isoformat(),
            'error': str(e),
            'tasks_active': len(tasks)
        }), 503

if __name__ == '__main__':
    # Start the background thread for cleaning up old tasks
    cleanup_thread = threading.Thread(target=cleanup_old_tasks, daemon=True)
    cleanup_thread.start()
    logger.info("Task cleanup thread started.")

    # Development mode - force debug ON for easier troubleshooting
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.run(debug=True, threaded=True, host='127.0.0.1', port=5000)
