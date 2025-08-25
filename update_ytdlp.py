#!/usr/bin/env python3
"""
Script to update yt-dlp to the latest version and test YouTube functionality
"""

import subprocess
import sys
import os
import yt_dlp

def run_command(cmd):
    """Run a command and return the result"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def update_ytdlp():
    """Update yt-dlp to the latest version"""
    print("🔄 Updating yt-dlp to the latest version...")
    
    # Try pip update first
    success, stdout, stderr = run_command("python -m pip install --upgrade yt-dlp")
    
    if success:
        print("✅ yt-dlp updated successfully via pip")
        print(f"Output: {stdout}")
    else:
        print("❌ Failed to update via pip, trying direct yt-dlp update...")
        print(f"Error: {stderr}")
        
        # Try yt-dlp self-update
        success, stdout, stderr = run_command("yt-dlp -U")
        if success:
            print("✅ yt-dlp updated successfully via self-update")
        else:
            print("❌ Failed to update yt-dlp")
            print(f"Error: {stderr}")
            return False
    
    return True

def test_youtube_download():
    """Test YouTube download functionality"""
    print("\n🧪 Testing YouTube download functionality...")
    
    # Test URL - Rick Astley (should always work)
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    
    try:
        # Test info extraction
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
            'extractor_args': {
                'youtube': {
                    'player_client': ['android_creator', 'android', 'web'],
                }
            }
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(test_url, download=False)
            
        print(f"✅ Successfully extracted info for: {info.get('title')}")
        print(f"📊 Available formats: {len(info.get('formats', []))}")
        print(f"⏱️ Duration: {info.get('duration')} seconds")
        print(f"👁️ Views: {info.get('view_count'):,}" if info.get('view_count') else "👁️ Views: Unknown")
        
        # Show some format examples
        formats = info.get('formats', [])
        if formats:
            print("\n📋 Sample formats available:")
            for i, fmt in enumerate(formats[:5]):  # Show first 5 formats
                resolution = fmt.get('resolution', 'Unknown')
                ext = fmt.get('ext', 'Unknown')
                format_id = fmt.get('format_id', 'Unknown')
                print(f"  {i+1}. ID: {format_id}, Resolution: {resolution}, Extension: {ext}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        return False

def check_ffmpeg():
    """Check if ffmpeg is available"""
    print("\n🔧 Checking ffmpeg availability...")
    
    ffmpeg_paths = [
        os.environ.get('FFMPEG_LOCATION'),
        os.environ.get('FFMPEG_PATH'),
        'ffmpeg'
    ]
    
    for path in ffmpeg_paths:
        if not path:
            continue
            
        success, stdout, stderr = run_command(f'"{path}" -version')
        if success:
            version_line = stdout.split('\n')[0] if stdout else "Unknown version"
            print(f"✅ ffmpeg found: {version_line}")
            return True
    
    print("⚠️ ffmpeg not found. Video merging may not work properly.")
    print("💡 Install ffmpeg and set FFMPEG_LOCATION environment variable for best results.")
    return False

def main():
    """Main function"""
    print("🚀 YouTube Downloader - Update and Test Script")
    print("=" * 50)
    
    # Check current version
    try:
        current_version = yt_dlp.version.__version__
        print(f"📦 Current yt-dlp version: {current_version}")
    except:
        print("❌ Could not determine current yt-dlp version")
    
    # Update yt-dlp
    if update_ytdlp():
        # Check new version
        try:
            # Reload the module to get new version
            import importlib
            importlib.reload(yt_dlp.version)
            new_version = yt_dlp.version.__version__
            print(f"📦 New yt-dlp version: {new_version}")
        except:
            print("📦 yt-dlp updated (version check failed)")
    
    # Check ffmpeg
    check_ffmpeg()
    
    # Test functionality
    if test_youtube_download():
        print("\n🎉 All tests passed! YouTube downloader should work properly.")
    else:
        print("\n❌ Tests failed. There may be issues with YouTube downloading.")
        print("💡 Try running the main app and check the logs for more details.")
    
    print("\n" + "=" * 50)
    print("✨ Update and test complete!")

if __name__ == "__main__":
    main()