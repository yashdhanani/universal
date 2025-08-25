#!/usr/bin/env python3
"""
Production-optimized configuration for maximum performance
"""

def get_production_ydl_opts():
    """Get production-optimized yt-dlp options for maximum speed"""
    return {
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
        'socket_timeout': 10,  # Even faster timeout
        'retries': 1,  # Minimal retries for speed
        'fragment_retries': 1,
        'skip_unavailable_fragments': True,
        'concurrent_fragment_downloads': 8,  # More aggressive
        'http_chunk_size': 16777216,  # 16MB chunks for speed
        'sleep_interval': 0,
        'max_sleep_interval': 0,
        'sleep_interval_subtitles': 0,
        # Minimal headers for speed
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        },
        # Skip unnecessary processing
        'writesubtitles': False,
        'writeautomaticsub': False,
        'writedescription': False,
        'writeinfojson': False,
        'writethumbnail': False,
        'extract_flat': False,
        'lazy_playlist': True,
        # Speed-focused format sorting
        'format_sort': ['res', 'fps', 'br'],
    }

def get_ultra_fast_format_filter():
    """Get ultra-fast format filtering function"""
    import re
    
    # Pre-compile patterns for maximum speed
    skip_patterns = re.compile(r'(m3u8|hls|premium|storyboard|dash)', re.IGNORECASE)
    
    def filter_format(f):
        """Ultra-fast format filter"""
        # Skip if no height (audio-only)
        if not f.get('height'):
            return False
            
        # Skip problematic formats
        protocol = f.get('protocol', '')
        format_note = f.get('format_note', '')
        
        if skip_patterns.search(protocol) or skip_patterns.search(format_note):
            return False
            
        return True
    
    return filter_format

def process_formats_ultra_fast(formats, max_formats=12):
    """Process formats with maximum speed optimization"""
    if not formats:
        return []
    
    filter_func = get_ultra_fast_format_filter()
    seen_resolutions = set()
    result = []
    
    # Process only first 20 formats for speed
    for f in formats[:20]:
        if not filter_func(f):
            continue
            
        height = f.get('height', 0)
        fps = f.get('fps', 0)
        
        # Simple deduplication by resolution
        res_key = f"{height}_{fps}"
        if res_key in seen_resolutions:
            continue
        seen_resolutions.add(res_key)
        
        # Minimal format object
        result.append({
            'format_id': f.get('format_id'),
            'ext': f.get('ext', 'mp4'),
            'quality': f"{height}p" + (f" {fps}fps" if fps > 30 else ""),
            'filesize_mb': round(f.get('filesize', 0) / 1048576, 1) if f.get('filesize') else None,
            'resolution': f"{f.get('width', 0)}x{height}",
            'fps': fps,
            'tbr': f.get('tbr'),
        })
        
        if len(result) >= max_formats:
            break
    
    return result

# Production server settings
PRODUCTION_SETTINGS = {
    'cache_duration': 600,  # 10 minutes cache
    'max_formats': 12,      # Limit formats for speed
    'timeout': 8,           # Faster timeout
    'max_retries': 1,       # Minimal retries
}