"""
Universal Download Task
Supports all platforms with automatic cookies management
"""

import os
import re
import logging
from typing import Dict, Any, Optional
import yt_dlp

from .celery_app import celery
from .progress import set_progress
from ..platforms.base import build_ydl_opts
from ..auth_manager import auth_manager
from ..utils.post_download import run_post_download

logger = logging.getLogger(__name__)


def _find_final_file(outdir: str, video_id: Optional[str]) -> str:
    """Find the newest file for the video id in outdir."""
    chosen = None
    newest = -1
    for f in os.listdir(outdir):
        if (not video_id) or (video_id in f):
            p = os.path.join(outdir, f)
            if os.path.isfile(p):
                m = os.path.getmtime(p)
                if m > newest:
                    newest = m
                    chosen = p
    if not chosen:
        raise RuntimeError("File not found after download/merge")
    return chosen


def _detect_platform(url: str) -> str:
    """Detect platform from URL"""
    platform_patterns = {
        'youtube': [r'youtube\.com', r'youtu\.be'],
        'instagram': [r'instagram\.com'],
        'facebook': [r'facebook\.com', r'fb\.watch'],
        'twitter': [r'twitter\.com', r'x\.com'],
        'tiktok': [r'tiktok\.com'],
        'pinterest': [r'pinterest\.com'],
        'snapchat': [r'snapchat\.com'],
        'linkedin': [r'linkedin\.com'],
        'reddit': [r'reddit\.com'],
        'naver': [r'(?:^|\.)naver\.com', r'video\.naver\.com', r'tv\.naver\.com']
    }
    
    for platform, patterns in platform_patterns.items():
        if any(re.search(pattern, url, re.IGNORECASE) for pattern in patterns):
            return platform
    
    return 'unknown'


def _prepare_download_opts(url: str, format_id: str, platform: str) -> tuple:
    """Prepare download options with platform-specific settings"""
    outdir = os.path.abspath("downloads")
    os.makedirs(outdir, exist_ok=True)
    
    # Base options with platform-specific cookies
    ydl_opts = build_ydl_opts(platform=platform)
    
    # Platform-specific output template
    if platform == 'youtube':
        outtmpl = os.path.join(outdir, "%(title)s [%(id)s].%(ext)s")
    elif platform == 'instagram':
        outtmpl = os.path.join(outdir, "%(uploader)s - %(title)s [%(id)s].%(ext)s")
    elif platform == 'tiktok':
        outtmpl = os.path.join(outdir, "TikTok - %(uploader)s - %(title)s [%(id)s].%(ext)s")
    elif platform == 'twitter':
        outtmpl = os.path.join(outdir, "Twitter - %(uploader)s - %(title)s [%(id)s].%(ext)s")
    else:
        outtmpl = os.path.join(outdir, f"{platform.title()} - %(uploader)s - %(title)s [%(id)s].%(ext)s")
    
    ydl_opts.update({
        'outtmpl': outtmpl,
        'writeinfojson': False,
        'writesubtitles': False,
        'writeautomaticsub': False,
    })

    # Prefer quality-preserving container for YouTube merges
    if platform == 'youtube':
        ydl_opts.setdefault('merge_output_format', 'mkv')
    
    # Format selection logic
    if format_id == "best":
        if platform == 'youtube':
            # For YouTube, prefer MP4 with audio
            ydl_opts['format'] = 'best[ext=mp4]/best'
        elif platform in ['instagram', 'facebook']:
            # For Instagram/Facebook, handle both video and image posts
            ydl_opts['format'] = 'best'
        else:
            ydl_opts['format'] = 'best'
    elif re.match(r"(?i)^mp3[_-]?(\d{2,3})$", str(format_id or "")):
        # Bitrate-suffixed MP3 id (e.g., mp3_128 → preferredquality=128)
        m = re.match(r"(?i)^mp3[_-]?(\d{2,3})$", str(format_id or ""))
        bitrate = int(m.group(1)) if m else 192
        # Clamp bitrate to 32–320 kbps and warn
        clamped = max(32, min(320, bitrate))
        if clamped != bitrate:
            try:
                logger.warning(f"mp3 bitrate {bitrate} out of range; clamped to {clamped}")
            except Exception:
                pass
        ydl_opts['format'] = 'bestaudio/best'
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': str(clamped),
        }]
        # Save MP3 without [id] suffix: Title.mp3
        ydl_opts['outtmpl'] = os.path.join(outdir, "%(title)s.%(ext)s")
        # Ensure we don't force a video container merge when extracting audio
        ydl_opts.pop('merge_output_format', None)
    elif format_id == "audio":
        ydl_opts['format'] = 'bestaudio/best'
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]
    else:
        # Specific format requested
        if platform == 'youtube' and '+' not in format_id:
            # Check if it's video-only format that needs audio
            try:
                with yt_dlp.YoutubeDL({'quiet': True}) as temp_ydl:
                    info = temp_ydl.extract_info(url, download=False)
                    formats = info.get('formats', [])
                    selected_format = next((f for f in formats if f.get('format_id') == format_id), None)
                    
                    if selected_format and selected_format.get('vcodec') != 'none' and selected_format.get('acodec') == 'none':
                        # Video-only format, merge with best audio
                        ydl_opts['format'] = f"{format_id}+bestaudio/best"
                    else:
                        ydl_opts['format'] = format_id
            except:
                ydl_opts['format'] = format_id
        else:
            ydl_opts['format'] = format_id
    
    return ydl_opts, outdir


@celery.task(bind=True, name="download.universal")
def universal_download_task(self, url: str, format_id: str = "best", platform: str = None) -> Dict[str, Any]:
    """Universal download task supporting all platforms with cookies"""
    task_id = self.request.id
    
    # Auto-detect platform if not provided
    if not platform:
        platform = _detect_platform(url)

    # Disable server-side download for Facebook
    if str(platform).lower() == 'facebook':
        raise RuntimeError("Server-side download is disabled for Facebook. Use instant download instead.")
    
    set_progress(task_id, "preparing", detail=f"Preparing {platform} download...")
    
    try:
        ydl_opts, outdir = _prepare_download_opts(url, format_id, platform)
        
        def hook(d):
            st = d.get("status")
            if st == "downloading":
                p_str = (d.get("_percent_str") or "").strip().replace("%", "")
                try:
                    percent = float(p_str) if p_str else None
                except Exception:
                    percent = None
                
                # Get speed and ETA
                speed = d.get("speed")
                eta = d.get("eta")
                
                detail = "Downloading"
                if speed:
                    speed_mb = speed / (1024 * 1024)
                    detail += f" ({speed_mb:.1f} MB/s)"
                
                set_progress(task_id, "downloading", percent=percent, eta=eta, detail=detail)
                
            elif st in ("finished", "complete"):
                set_progress(task_id, "processing", detail="Processing file...")
            elif st == "error":
                set_progress(task_id, "error", detail=f"Download error: {d.get('error', 'Unknown error')}")
        
        ydl_opts["progress_hooks"] = [hook]
        
        # Attempt download with cookies
        set_progress(task_id, "downloading", detail="Starting download...")
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
        
        if not info:
            raise RuntimeError("Failed to extract video information")
        
        # Handle playlist vs single video
        if info.get('_type') == 'playlist':
            # For playlists, get the first entry
            entries = info.get('entries', [])
            if entries:
                info = entries[0]
            else:
                raise RuntimeError("Empty playlist")
        
        video_id = info.get("id")
        title = info.get("title", "Unknown")
        uploader = info.get("uploader", "Unknown")
        
        # Find the downloaded file
        final_path = _find_final_file(outdir, video_id)
        
        set_progress(task_id, "finished", percent=100.0, eta=0, detail="Download completed!")
        
        result = {
            "success": True,
            "path": final_path,
            "filename": os.path.basename(final_path),
            "id": video_id,
            "title": title,
            "uploader": uploader,
            "platform": platform,
            "ext": os.path.splitext(final_path)[1].lstrip("."),
            "filesize": os.path.getsize(final_path),
            "url": url,
            "format_id": format_id,
            "thumbnail": info.get("thumbnail") if isinstance(info, dict) else None,
        }
        try:
            run_post_download(result, success=True)
        except Exception:
            pass
        return result
        
    except Exception as e:
        error_msg = str(e)
        set_progress(task_id, "error", detail=f"Download failed: {error_msg}")
        
        # Check if it's a cookies-related error
        if any(keyword in error_msg.lower() for keyword in ['login', 'private', 'forbidden', '403', 'unauthorized', '401']):
            cookies_hint = f"This content may require login cookies. Visit /cookies to upload {platform} cookies."
            set_progress(task_id, "error", detail=f"{error_msg}\n\n💡 {cookies_hint}")
        
        failure = {
            "success": False,
            "error": error_msg,
            "platform": platform,
            "url": url,
            "cookies_required": any(keyword in error_msg.lower() for keyword in ['login', 'private', 'forbidden', '403', 'unauthorized', '401'])
        }
        try:
            run_post_download(failure, success=False, error=error_msg)
        except Exception:
            pass
        return failure


# Legacy compatibility - redirect old YouTube task to universal
@celery.task(bind=True, name="download.youtube")
def youtube_download_task(self, url: str, format_id: str) -> Dict[str, Any]:
    """Legacy YouTube download task - redirects to universal"""
    return universal_download_task.apply_async(args=[url, format_id, 'youtube']).get()


# Platform-specific convenience tasks
@celery.task(bind=True, name="download.instagram")
def instagram_download_task(self, url: str, format_id: str = "best") -> Dict[str, Any]:
    """Instagram download task"""
    return universal_download_task.apply_async(args=[url, format_id, 'instagram']).get()


@celery.task(bind=True, name="download.tiktok")
def tiktok_download_task(self, url: str, format_id: str = "best") -> Dict[str, Any]:
    """TikTok download task"""
    return universal_download_task.apply_async(args=[url, format_id, 'tiktok']).get()


@celery.task(bind=True, name="download.twitter")
def twitter_download_task(self, url: str, format_id: str = "best") -> Dict[str, Any]:
    """Twitter download task"""
    return universal_download_task.apply_async(args=[url, format_id, 'twitter']).get()


@celery.task(bind=True, name="download.facebook")
def facebook_download_task(self, url: str, format_id: str = "best") -> Dict[str, Any]:
    """Facebook download task"""
    return universal_download_task.apply_async(args=[url, format_id, 'facebook']).get()