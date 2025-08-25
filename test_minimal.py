#!/usr/bin/env python3
"""
Test minimal yt-dlp configuration that works
"""

import yt_dlp
import time

def test_minimal_config():
    """Test with minimal configuration"""
    print("🔧 Testing Minimal Configuration")
    print("=" * 40)
    
    test_url = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
    
    # Minimal working configuration
    opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'socket_timeout': 15,
        'retries': 2,
    }
    
    try:
        print(f"🔄 Testing URL: {test_url}")
        start_time = time.time()
        
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(test_url, download=False)
        
        end_time = time.time()
        fetch_time = end_time - start_time
        
        print(f"✅ Success: {fetch_time:.2f}s")
        print(f"   Title: {info.get('title', 'Unknown')[:50]}")
        print(f"   Duration: {info.get('duration', 0)}s")
        print(f"   Formats: {len(info.get('formats', []))}")
        
        # Show some format details
        formats = info.get('formats', [])[:5]  # First 5 formats
        print("   Sample formats:")
        for f in formats:
            print(f"     {f.get('format_id')}: {f.get('ext')} {f.get('height', 'audio')}p")
        
        return True, opts
        
    except Exception as e:
        print(f"❌ Minimal test failed: {str(e)[:100]}...")
        return False, None

def test_android_client():
    """Test with android client specifically"""
    print("\n🤖 Testing Android Client")
    print("=" * 40)
    
    test_url = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
    
    # Android client configuration
    opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'socket_timeout': 15,
        'retries': 2,
        'extractor_args': {
            'youtube': {
                'player_client': ['android'],
            }
        }
    }
    
    try:
        print(f"🔄 Testing URL: {test_url}")
        start_time = time.time()
        
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(test_url, download=False)
        
        end_time = time.time()
        fetch_time = end_time - start_time
        
        print(f"✅ Success: {fetch_time:.2f}s")
        print(f"   Title: {info.get('title', 'Unknown')[:50]}")
        print(f"   Duration: {info.get('duration', 0)}s")
        print(f"   Formats: {len(info.get('formats', []))}")
        
        return True, opts
        
    except Exception as e:
        print(f"❌ Android client test failed: {str(e)[:100]}...")
        return False, None

def main():
    """Main test function"""
    print("🚀 Minimal Configuration Test")
    print("=" * 50)
    
    # Test 1: Minimal config
    minimal_ok, minimal_opts = test_minimal_config()
    
    # Test 2: Android client
    android_ok, android_opts = test_android_client()
    
    print("\n" + "=" * 50)
    print("📊 RESULTS")
    print("=" * 50)
    
    if minimal_ok:
        print("✅ Minimal config works!")
        print("   Recommended for server use")
    
    if android_ok:
        print("✅ Android client works!")
        print("   Good for compatibility")
    
    if minimal_ok or android_ok:
        working_opts = minimal_opts if minimal_ok else android_opts
        print("\n🔧 Working Configuration:")
        for key, value in working_opts.items():
            print(f"   '{key}': {value}")
    else:
        print("❌ No configuration works")
        print("   Check network or yt-dlp installation")

if __name__ == "__main__":
    main()