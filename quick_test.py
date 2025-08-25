#!/usr/bin/env python3
"""
Quick test script to verify YouTube Downloader functionality
"""

import os
import sys
import yt_dlp
from datetime import datetime

def test_basic_extraction():
    """Test basic YouTube video extraction"""
    print("🧪 Testing YouTube video extraction...")
    
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # Rick Roll
    
    try:
        # Enhanced yt-dlp options for 2025
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
            'socket_timeout': 15,
            'retries': 3,
            'extractor_args': {
                'youtube': {
                    'player_client': ['android_creator', 'android', 'web'],
                    'skip': ['hls', 'dash']
                }
            },
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                'Accept-Language': 'en-US,en;q=0.9',
                'Referer': 'https://www.youtube.com/',
            }
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(test_url, download=False)
        
        title = info.get('title', 'Unknown')
        duration = info.get('duration', 0)
        formats = info.get('formats', [])
        
        print(f"✅ Extraction successful!")
        print(f"   Title: {title}")
        print(f"   Duration: {duration} seconds")
        print(f"   Formats available: {len(formats)}")
        
        # Show some format examples
        if formats:
            print("   Sample formats:")
            for i, fmt in enumerate(formats[:3]):
                resolution = fmt.get('resolution', 'Unknown')
                ext = fmt.get('ext', 'Unknown')
                format_id = fmt.get('format_id', 'Unknown')
                print(f"     {i+1}. {format_id}: {resolution} ({ext})")
        
        return True
        
    except Exception as e:
        print(f"❌ Extraction failed: {str(e)}")
        return False

def test_multiple_clients():
    """Test different YouTube clients"""
    print("\n🔄 Testing different YouTube clients...")
    
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    clients = ['android_creator', 'android_music', 'android', 'web', 'ios']
    
    working_clients = []
    
    for client in clients:
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'skip_download': True,
                'socket_timeout': 10,
                'extractor_args': {
                    'youtube': {
                        'player_client': client,
                        'skip': ['hls', 'dash'] if client.startswith('android') else ['hls']
                    }
                }
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(test_url, download=False)
            
            formats_count = len(info.get('formats', []))
            print(f"   ✅ {client}: {formats_count} formats")
            working_clients.append(client)
            
        except Exception as e:
            print(f"   ❌ {client}: {str(e)[:50]}...")
    
    print(f"\n📊 Working clients: {len(working_clients)}/{len(clients)}")
    if working_clients:
        print(f"   Best clients: {', '.join(working_clients[:3])}")
        return True
    else:
        print("   ⚠️ No clients working - may have connectivity issues")
        return False

def test_app_import():
    """Test if the main app can be imported"""
    print("\n📦 Testing app import...")
    
    try:
        from app import app, build_ydl_opts
        print("✅ Main app imported successfully")
        
        # Test ydl_opts building
        opts = build_ydl_opts()
        print(f"✅ yt-dlp options built successfully")
        print(f"   User-Agent: {opts['http_headers']['User-Agent'][:50]}...")
        print(f"   Clients: {opts['extractor_args']['youtube']['player_client']}")
        
        return True
        
    except Exception as e:
        print(f"❌ App import failed: {str(e)}")
        return False

def main():
    """Main test function"""
    print("🚀 YouTube Downloader - Quick Test")
    print("=" * 40)
    print(f"⏰ Test started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🐍 Python version: {sys.version.split()[0]}")
    
    try:
        print(f"📦 yt-dlp version: {yt_dlp.version.__version__}")
    except:
        print("📦 yt-dlp version: Unknown")
    
    print()
    
    # Run tests
    tests = [
        ("App Import", test_app_import),
        ("Basic Extraction", test_basic_extraction),
        ("Multiple Clients", test_multiple_clients),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"🔄 Running {test_name}...")
        if test_func():
            passed += 1
        print()
    
    # Summary
    print("=" * 40)
    print(f"📊 Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All tests passed! YouTube Downloader is ready to use.")
        print("🚀 Run 'python start_fixed.py' or 'start_development.bat' to start the server.")
    elif passed >= total * 0.5:
        print("⚠️ Some tests failed, but basic functionality should work.")
        print("🔧 Run 'python troubleshoot.py' for detailed diagnostics.")
    else:
        print("❌ Multiple tests failed. There may be serious issues.")
        print("🔧 Run 'python troubleshoot.py' for help.")
    
    print("=" * 40)

if __name__ == "__main__":
    main()