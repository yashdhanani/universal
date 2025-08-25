"""
YouTube Downloader Fix Script
Addresses the main issues causing download failures:
1. HTTP 403 Forbidden errors
2. Missing cookies authentication
3. Format availability issues
4. Incomplete downloads (.part files)
"""

import os
import shutil
import yt_dlp
from datetime import datetime
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def clean_partial_downloads():
    """Remove all .part files from downloads folder"""
    downloads_dir = 'downloads'
    if not os.path.exists(downloads_dir):
        return
    
    part_files = [f for f in os.listdir(downloads_dir) if f.endswith('.part')]
    for part_file in part_files:
        try:
            os.remove(os.path.join(downloads_dir, part_file))
            logger.info(f"Removed partial file: {part_file}")
        except Exception as e:
            logger.error(f"Failed to remove {part_file}: {e}")
    
    logger.info(f"Cleaned {len(part_files)} partial download files")

def get_enhanced_ydl_opts():
    """Get enhanced yt-dlp options with better anti-bot measures"""
    return {
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
        'geo_bypass': True,
        'socket_timeout': 30,
        'retries': 5,
        'fragment_retries': 5,
        'skip_unavailable_fragments': True,
        'concurrent_fragment_downloads': 1,  # Reduced to avoid rate limiting
        'sleep_interval': 1,  # Add delay between requests
        'max_sleep_interval': 5,
        'sleep_interval_subtitles': 1,
        # Enhanced headers to better mimic real browser
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
        },
        # Use multiple extraction strategies
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'web'],  # Try multiple clients
                'player_skip': ['webpage', 'configs'],
                'skip': ['hls', 'dash'],  # Skip problematic formats
            }
        },
        # Format selection with fallbacks
        'format': 'best[height<=720][ext=mp4]/best[ext=mp4]/best[height<=480]/worst[ext=mp4]/best',
        'merge_output_format': 'mp4',  # Use MP4 instead of MKV for better compatibility
        'writesubtitles': False,
        'writeautomaticsub': False,
        'ignoreerrors': False,
        'extract_flat': False,
    }

def test_download(url):
    """Test download with enhanced options"""
    logger.info(f"Testing download for: {url}")
    
    # Clean up any existing partial files first
    clean_partial_downloads()
    
    # Create unique filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    outtmpl = os.path.join('downloads', f'test_download_{timestamp}.%(ext)s')
    
    ydl_opts = get_enhanced_ydl_opts()
    ydl_opts['outtmpl'] = outtmpl
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # First, try to extract info
            logger.info("Extracting video information...")
            info = ydl.extract_info(url, download=False)
            logger.info(f"Video title: {info.get('title', 'Unknown')}")
            logger.info(f"Duration: {info.get('duration', 'Unknown')} seconds")
            
            # Show available formats
            formats = info.get('formats', [])
            logger.info(f"Available formats: {len(formats)}")
            
            # Try download with most compatible format
            logger.info("Starting download...")
            ydl.download([url])
            
            # Check if file was created
            downloads_dir = 'downloads'
            files = [f for f in os.listdir(downloads_dir) if f.startswith('test_download_')]
            if files:
                latest_file = max(files, key=lambda x: os.path.getctime(os.path.join(downloads_dir, x)))
                logger.info(f"Download successful: {latest_file}")
                return True
            else:
                logger.error("Download completed but no file found")
                return False
                
    except yt_dlp.DownloadError as e:
        logger.error(f"Download error: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return False

def create_cookies_template():
    """Create a template cookies.txt file with instructions"""
    cookies_content = """# Netscape HTTP Cookie File
# This is a generated file! Do not edit.
# 
# To fix YouTube download issues, you need to export cookies from your browser:
# 
# For Chrome:
# 1. Install "Get cookies.txt LOCALLY" extension
# 2. Go to youtube.com and make sure you're logged in
# 3. Click the extension icon and download cookies.txt
# 4. Replace this file with the downloaded cookies.txt
# 
# For Firefox:
# 1. Install "cookies.txt" addon
# 2. Go to youtube.com and make sure you're logged in  
# 3. Click the addon icon and export cookies
# 4. Replace this file with the exported cookies.txt
#
# Without proper cookies, many YouTube videos will fail to download due to 403 errors.
"""
    
    with open('cookies.txt', 'w', encoding='utf-8') as f:
        f.write(cookies_content)
    
    logger.info("Created cookies.txt template with instructions")

def main():
    """Main function to test and fix downloader issues"""
    logger.info("YouTube Downloader Fix Script Starting...")
    
    # Create cookies template
    create_cookies_template()
    
    # Clean partial downloads
    clean_partial_downloads()
    
    # Test with a known working video (Rick Astley - Never Gonna Give You Up)
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    
    logger.info("Testing download functionality...")
    success = test_download(test_url)
    
    if success:
        logger.info("✅ Download test PASSED - Downloader is working!")
    else:
        logger.error("❌ Download test FAILED - Issues remain")
        logger.info("Recommendations:")
        logger.info("1. Export cookies from your browser to cookies.txt")
        logger.info("2. Install ffmpeg for video processing")
        logger.info("3. Check your internet connection")
        logger.info("4. Try again with different videos")

if __name__ == "__main__":
    main()
