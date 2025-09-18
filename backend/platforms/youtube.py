import re
import os
import yt_dlp
from .base import build_ydl_opts
from ..utils.cache import cache_video_analysis

# Performance optimization: pre-compiled regex for faster filtering
HLS_PATTERN = re.compile(r'm3u8|hls', re.IGNORECASE)
PREMIUM_PATTERN = re.compile(r'premium|storyboard', re.IGNORECASE)

PLATFORM_NAME = "youtube"
URL_PATTERNS = [
    re.compile(r"https?://(www\.)?youtube\.com/", re.I),
    re.compile(r"https?://youtu\.be/", re.I),
]

@cache_video_analysis("youtube")
def analyze(url: str):
    """Analyze a YouTube URL and return media info and formats."""
    if not any(p.search(url or "") for p in URL_PATTERNS):
        raise ValueError("Invalid YouTube URL")

    try:
        # Detect playlist/channel/handle URLs (tabs) and use flat extraction
        lower_url = (url or "").lower()
        is_playlist_like = (
            "youtube.com/playlist" in lower_url
            or "list=" in lower_url
            or "youtube.com/@" in lower_url
            or "youtube.com/channel/" in lower_url
            or "youtube.com/c/" in lower_url
            or "youtube.com/user/" in lower_url
        )

        if is_playlist_like:
            # First attempt: fast flat extraction
            try:
                ydl_opts = build_ydl_opts({
                    'skip_download': True,
                    'noplaylist': False,
                    'extract_flat': 'discard_in_playlist',
                    'extractor_retries': 1,
                    'http_headers': {'Referer': url, 'Origin': 'https://www.youtube.com'}
                }, platform='youtube')
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
            except Exception:
                # Fallback: smaller page size and permissive flat mode
                ydl_opts = build_ydl_opts({
                    'skip_download': True,
                    'noplaylist': False,
                    'extract_flat': 'in_playlist',
                    'playlistend': 100,  # cap for very large channels/playlists
                    'extractor_retries': 2,
                    'http_headers': {'Referer': url, 'Origin': 'https://www.youtube.com'},
                    # Force web client behavior implicitly
                }, platform='youtube')
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)

            if not info:
                raise ConnectionError('Failed to extract playlist/channel')

            entries = info.get('entries') or []
            items = []
            for e in entries:
                try:
                    items.append({
                        'id': e.get('id'),
                        'title': e.get('title'),
                        'duration': e.get('duration'),
                        'thumbnail': e.get('thumbnail'),
                        'uploader': e.get('uploader') or e.get('channel'),
                        'webpage_url': e.get('url') or e.get('webpage_url'),
                    })
                except Exception:
                    continue

            return {
                'title': info.get('title') or 'Playlist/Channel',
                'thumbnail': info.get('thumbnail', ''),
                'duration': None,
                'uploader': info.get('uploader') or info.get('channel') or 'Unknown',
                'mp4': [],
                'mp3': [],
                'items': items,
                'count': len(items),
            }

        # Prefer iOS client first (often exposes direct progressive MP4 URLs), then web, then android
        clients = ['ios', 'web', 'android']
        combined_formats = []
        info = None
        last_error = None
        
        for client in clients:
            try:
                ydl_opts = build_ydl_opts({
                    'skip_download': True,
                    'extractor_args': {'youtube': {'player_client': client}},
                    'http_headers': {'Referer': url, 'Origin': 'https://www.youtube.com'}
                }, platform='youtube')
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info_try = ydl.extract_info(url, download=False)
                
                fmts = info_try.get('formats') or []
                if fmts:
                    combined_formats.extend(fmts)
                    # Keep the first successful info for metadata (title, duration, etc.)
                    if info is None:
                        info = info_try
            except Exception as ce:
                last_error = str(ce)
                continue
        
        if not combined_formats:
            raise ConnectionError(last_error or 'Failed to extract formats from all clients')
        if info is None:
            # As a fallback, synthesize minimal info
            info = {'title': 'YouTube Video'}

        # Prefer progressive (video+audio) when duplicates (same height/fps/ext) exist.
        # Also aggressively prefer MP4 with direct URLs.
        formats_map = {}
        source_formats = combined_formats
        
        def pref_tuple(is_prog: bool, ext: str, has_direct: bool, height: int, fps: int, tbr: float):
            return (
                1 if is_prog else 0,
                1 if (ext or '').lower() == 'mp4' else 0,
                1 if has_direct else 0,
                height or 0,
                fps or 0,
                tbr or 0.0,
            )
        
        for f in source_formats:
            protocol = f.get('protocol', '')
            format_note = f.get('format_note', '')
            
            if (HLS_PATTERN.search(protocol) or PREMIUM_PATTERN.search(format_note)):
                continue
            
            height = f.get('height') or 0
            if height <= 0:
                continue
            
            fps = f.get('fps') or 0
            ext = f.get('ext') or 'mp4'
            
            key = f"{height}_{fps}_{ext}"
            has_video = (f.get('vcodec') and f.get('vcodec') != 'none')
            has_audio = (f.get('acodec') and f.get('acodec') != 'none')
            progressive = bool(has_video and has_audio)

            filesize = f.get('filesize') or f.get('filesize_approx')
            if filesize and filesize > 0:
                filesize_mb = round(filesize / 1048576, 1)
            else:
                # Estimate size from bitrate (tbr in kbps) and duration (s): MB ≈ tbr*duration/8/1024
                duration = info.get('duration') or 0
                tbr = f.get('tbr') or 0
                filesize_mb = round((tbr * duration) / 8 / 1024, 1) if (duration and tbr) else None
            
            has_direct_url = bool(f.get('url'))
            new_entry = {
                'format_id': f.get('format_id'),
                'ext': ext,
                'quality': f.get('format_note', f"{height}p"),
                'filesize_mb': filesize_mb,
                'resolution': f"{f.get('width', 0)}x{height}" if height > 0 else None,
                'height': height,
                'fps': fps,
                'vcodec': f.get('vcodec'),
                'acodec': f.get('acodec'),
                'tbr': f.get('tbr'),
                'is_progressive': progressive,
                'has_direct_url': has_direct_url,
                'url': f.get('url') if progressive and has_direct_url else None,  # expose direct URL for instant progressive download
                'type': 'video'
            }
            
            existing = formats_map.get(key)
            if existing:
                # Replace only if the new one has a strictly better preference tuple
                new_score = pref_tuple(progressive, ext, has_direct_url, height, fps, f.get('tbr') or 0)
                old_score = pref_tuple(existing.get('is_progressive'), existing.get('ext'), existing.get('has_direct_url'), existing.get('height'), existing.get('fps'), existing.get('tbr') or 0)
                if new_score <= old_score:
                    continue
            formats_map[key] = new_entry

        formats = list(formats_map.values())
        # Sort to show the most desirable (progressive MP4 with direct URLs, higher res/fps) first
        formats.sort(key=lambda e: (
            1 if e.get('is_progressive') else 0,
            1 if (e.get('ext') or '').lower() == 'mp4' else 0,
            1 if e.get('has_direct_url') else 0,
            e.get('height') or 0,
            e.get('fps') or 0,
            e.get('tbr') or 0
        ), reverse=True)

        audio_formats = []
        audio_source_formats = [f for f in source_formats if (f.get('acodec') and f.get('acodec') != 'none') and (not f.get('vcodec') or f.get('vcodec') == 'none')]
        for f in audio_source_formats[:5]:
            abr = f.get('abr') or f.get('tbr') or 128
            filesize = f.get('filesize') or f.get('filesize_approx')
            filesize_mb = round(filesize / 1048576, 1) if filesize and filesize > 0 else None
            ext = (f.get('ext') or 'm4a').upper()
            audio_formats.append({
                'quality': f"Instant Audio {int(abr)} kbps" if abr else 'Instant Audio',
                'size': f"{filesize_mb:.1f} MB" if filesize_mb else 'Unknown size',
                'filesize_mb': filesize_mb,
                'format_id': f.get('format_id'),
                'ext': ext,
                'has_direct_url': bool(f.get('url')),
                'url': f.get('url'),
                'type': 'audio',
            })

        # Add fast MP3 conversion options (served via mp3_XXX format ids)
        try:
            duration_sec = int(info.get('duration')) if info.get('duration') else 0
        except Exception:
            duration_sec = 0
        for bitrate in [128, 192, 320]:
            est_mb = round((bitrate * duration_sec) / 8 / 1024, 1) if duration_sec else None
            audio_formats.append({
                'quality': f"Fast MP3 {bitrate} kbps",
                'size': f"{est_mb:.1f} MB" if est_mb else 'Unknown size',
                'filesize_mb': est_mb,
                'format_id': f"mp3_{bitrate}",
                'ext': 'MP3',
                'has_direct_url': False,
                'url': None,
                'type': 'audio',
            })

        return {
            'title': info.get('title', 'Unknown Title'),
            'thumbnail': info.get('thumbnail', ''),
            'duration': info.get('duration'),
            'uploader': info.get('uploader', 'Unknown'),
            'mp4': formats,
            'mp3': audio_formats,
            'items': [],
            'count': 1
        }

    except Exception as e:
        if "private" in str(e).lower():
            raise ValueError("This video is private.")
        if "unavailable" in str(e).lower():
            raise ValueError("This video is unavailable.")
        raise ConnectionError(f"Failed to analyze YouTube video: {e}")

def prepare_download(url: str, format_id: str):
    """Prepares yt-dlp options for a YouTube download.
    - Respects progressive formats exactly (no forced +bestaudio).
    - For video-only formats, merges with bestaudio.
    - For mp3_XXX, converts bestaudio to MP3 at requested bitrate.
    """
    # Default to the provided selector
    format_selector = format_id

    if format_id == 'best':
        # Prefer progressive MP4 > MP4 video-only + m4a > MP4 video-only + any > generic merge > best
        format_selector = (
            'best[ext=mp4][vcodec!=none][acodec!=none]/'
            'best[vcodec!=none][acodec!=none]/'
            'bestvideo[ext=mp4]+bestaudio[ext=m4a]/'
            'bestvideo[ext=mp4]+bestaudio/'
            'bestvideo+bestaudio/'
            'best'
        )
    elif format_id.startswith('mp3_'):
        # Handled below in postprocessors
        pass
    elif '+' in format_id:
        # Explicit selector provided by caller (e.g., "137+bestaudio")
        format_selector = format_id
    else:
        # Decide whether the requested format is video-only or progressive
        try:
            with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                info = ydl.extract_info(url, download=False)
            fmts = info.get('formats') or []
            sel = next((f for f in fmts if str(f.get('format_id')) == str(format_id)), None)
            if sel:
                has_video = (sel.get('vcodec') and sel.get('vcodec') != 'none')
                has_audio = (sel.get('acodec') and sel.get('acodec') != 'none')
                if has_video and not has_audio:
                    # Video-only: merge with bestaudio (prefer m4a when available)
                    format_selector = (
                        f"{format_id}+bestaudio[ext=m4a]/"
                        f"{format_id}+bestaudio/"
                        f"{format_id}"
                    )
                else:
                    # Progressive (video+audio) or audio-only: respect exact id
                    format_selector = str(format_id)
            else:
                # Unknown id: best effort use it directly
                format_selector = str(format_id)
        except Exception:
            # On any error, fall back to using the provided id directly
            format_selector = str(format_id)

    # Build base options with performance tuning
    ydl_opts = build_ydl_opts({
        'format': format_selector,
        # Sort formats deterministically favoring progressive MP4 and quality
        'format_sort': ['hasaud', 'ext:mp4:m4a', 'res', 'fps', 'tbr', 'filesize'],
        'format_sort_force': True,
        'outtmpl': os.path.join(os.path.join(os.getcwd(), 'downloads', 'youtube'), '%(title)s [%(id)s].%(ext)s'),
        'merge_output_format': 'mkv',
        # Speed/tuning
        'retries': 5,
        'fragment_retries': 5,
        'file_access_retries': 3,
        'buffersize': 1024 * 1024,              # 1 MiB buffer
        'http_chunk_size': 16 * 1024 * 1024,    # 16 MiB chunks help ramp-up/resume
        'concurrent_fragment_downloads': 4,     # parallelism for fragmented streams
    }, platform='youtube')

    # Use aria2c when available for multi-connection downloads
    aria2c_path = os.environ.get('ARIA2C_PATH')
    if aria2c_path:
        ydl_opts['external_downloader'] = aria2c_path
        ydl_opts['external_downloader_args'] = {
            'aria2c': [
                '--max-connection-per-server=16',
                '--split=16',
                '--min-split-size=8M',
                '--allow-overwrite=true',
                '--console-log-level=warn',
                '--summary-interval=0',
            ]
        }

    # MP3 conversion path
    if format_id.startswith('mp3_'):
        try:
            bitrate = int(format_id.split('_')[1])
        except Exception:
            bitrate = 192
        ydl_opts['format'] = 'bestaudio'
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': str(bitrate),
        }]
        # Ensure MP3 files are saved without the [id] suffix: Title.mp3
        ydl_opts['outtmpl'] = os.path.join(os.path.join(os.getcwd(), 'downloads', 'youtube'), '%(title)s.%(ext)s')
        ydl_opts.pop('merge_output_format', None)

    outdir = os.path.join(os.getcwd(), 'downloads', 'youtube')
    os.makedirs(outdir, exist_ok=True)

    return ydl_opts, outdir
