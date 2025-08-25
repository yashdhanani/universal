#!/usr/bin/env python3
"""
Network and yt-dlp connectivity test
"""

import yt_dlp
import time
import requests
from datetime import datetime

def test_basic_connectivity():
    """Test basic network connectivity"""
    print("🌐 Testing Network Connectivity")
    print("=" * 40)
    
    try:
        # Test basic HTTP connectivity
        response = requests.get('https://www.google.com', timeout=10)
        print(f"✅ Google.com: {response.status_code}")
        
        # Test YouTube connectivity
        response = requests.get('https://www.youtube.com', timeout=10)
        print(f"✅ YouTube.com: {response.status_code}")
        
        return True
    except Exception as e:
        print(f"❌ Network test failed: {e}")
        return False

def test_ytdlp_direct():
    """Test yt-dlp directly without server"""
    print("\n🔧 Testing yt-dlp Direct")
    print("=" * 40)
    
    test_url = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
    
    # Simple yt-dlp options
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
        
        return True, fetch_time
        
    except Exception as e:
        print(f"❌ yt-dlp test failed: {str(e)[:100]}...")
        return False, 0

def test_server_endpoint():
    """Test server endpoint"""
    print("\n🖥️ Testing Server Endpoint")
    print("=" * 40)
    
    test_url = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
    
    try:
        print(f"🔄 Testing server with URL: {test_url}")
        start_time = time.time()
        
        response = requests.post(
            'http://127.0.0.1:5000/api/video_info',
            json={'url': test_url},
            timeout=30
        )
        
        end_time = time.time()
        fetch_time = end_time - start_time
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Server success: {fetch_time:.2f}s")
            print(f"   Title: {data.get('title', 'Unknown')[:50]}")
            print(f"   Formats: {len(data.get('formats', []))}")
            return True, fetch_time
        else:
            print(f"❌ Server failed: HTTP {response.status_code}")
            try:
                error_data = response.json()
                print(f"   Error: {error_data.get('error', 'Unknown error')[:100]}")
            except:
                print(f"   Raw response: {response.text[:100]}")
            return False, fetch_time
            
    except Exception as e:
        print(f"❌ Server test failed: {str(e)[:100]}...")
        return False, 0

def main():
    """Main test function"""
    print("🚀 Network and Performance Diagnostic Test")
    print("=" * 60)
    print(f"⏰ Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Test 1: Basic connectivity
    network_ok = test_basic_connectivity()
    
    if not network_ok:
        print("\n❌ Network connectivity failed. Check your internet connection.")
        return
    
    # Test 2: Direct yt-dlp
    ytdlp_ok, ytdlp_time = test_ytdlp_direct()
    
    # Test 3: Server endpoint
    server_ok, server_time = test_server_endpoint()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 DIAGNOSTIC SUMMARY")
    print("=" * 60)
    
    print(f"🌐 Network: {'✅ OK' if network_ok else '❌ FAILED'}")
    print(f"🔧 yt-dlp Direct: {'✅ OK' if ytdlp_ok else '❌ FAILED'}")
    if ytdlp_ok:
        print(f"   Time: {ytdlp_time:.2f}s")
    
    print(f"🖥️ Server: {'✅ OK' if server_ok else '❌ FAILED'}")
    if server_ok:
        print(f"   Time: {server_time:.2f}s")
        if ytdlp_ok:
            overhead = server_time - ytdlp_time
            print(f"   Overhead: {overhead:.2f}s")
    
    if ytdlp_ok and server_ok:
        print("\n🎉 ALL SYSTEMS WORKING!")
        print("✅ Performance optimizations are active")
        if server_time < 5:
            print("🚀 EXCELLENT: Very fast response times")
        elif server_time < 10:
            print("✅ GOOD: Acceptable response times")
        else:
            print("⚠️ SLOW: May need further optimization")
    elif ytdlp_ok:
        print("\n⚠️ yt-dlp works but server has issues")
        print("🔧 Check server logs for problems")
    else:
        print("\n❌ FUNDAMENTAL ISSUES DETECTED")
        print("🛠️ yt-dlp cannot connect to YouTube")
        print("💡 Try:")
        print("   • Check firewall settings")
        print("   • Update yt-dlp: pip install -U yt-dlp")
        print("   • Add cookies file for authentication")

if __name__ == "__main__":
    main()