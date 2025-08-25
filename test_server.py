#!/usr/bin/env python3
"""
Test the running YouTube Downloader server
"""

import requests
import json
import time
from datetime import datetime

def test_server_running():
    """Test if the server is running"""
    print("🔍 Testing if server is running...")
    
    try:
        response = requests.get('http://127.0.0.1:5000', timeout=5)
        if response.status_code == 200:
            print("✅ Server is running and responding!")
            print(f"   Status Code: {response.status_code}")
            print(f"   Content Length: {len(response.text)} characters")
            return True
        else:
            print(f"⚠️ Server responded with status code: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Server is not running or not accessible")
        return False
    except requests.exceptions.Timeout:
        print("⏰ Server request timed out")
        return False
    except Exception as e:
        print(f"❌ Error testing server: {e}")
        return False

def test_video_info_api():
    """Test the video info API"""
    print("\n🧪 Testing video info API...")
    
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    
    try:
        response = requests.post(
            'http://127.0.0.1:5000/api/video_info',
            json={'url': test_url},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Video info API working!")
            print(f"   Title: {data.get('title', 'Unknown')}")
            print(f"   Duration: {data.get('duration', 0)} seconds")
            print(f"   Formats available: {len(data.get('formats', []))}")
            
            # Show some format examples
            formats = data.get('formats', [])
            if formats:
                print("   Sample formats:")
                for i, fmt in enumerate(formats[:3]):
                    quality = fmt.get('quality', 'Unknown')
                    ext = fmt.get('ext', 'Unknown')
                    format_id = fmt.get('format_id', 'Unknown')
                    print(f"     {i+1}. {format_id}: {quality} ({ext})")
            
            return True
        else:
            print(f"❌ API returned status code: {response.status_code}")
            print(f"   Response: {response.text[:200]}...")
            return False
            
    except requests.exceptions.Timeout:
        print("⏰ API request timed out (this can be normal for first request)")
        return False
    except Exception as e:
        print(f"❌ Error testing API: {e}")
        return False

def test_download_api():
    """Test the download API (without actually downloading)"""
    print("\n🔽 Testing download API...")
    
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    
    try:
        response = requests.post(
            'http://127.0.0.1:5000/api/download',
            json={
                'url': test_url,
                'format_id': 'best[height<=480]'  # Low quality for testing
            },
            timeout=60
        )
        
        if response.status_code == 200:
            data = response.json()
            task_id = data.get('task_id')
            print("✅ Download API working!")
            print(f"   Task ID: {task_id}")
            print("   Download started successfully")
            
            # Test progress API
            if task_id:
                print("\n📊 Testing progress API...")
                time.sleep(2)  # Wait a bit
                
                progress_response = requests.get(
                    f'http://127.0.0.1:5000/api/progress/{task_id}',
                    timeout=5
                )
                
                if progress_response.status_code == 200:
                    progress_data = progress_response.json()
                    print("✅ Progress API working!")
                    print(f"   Status: {progress_data.get('status', 'Unknown')}")
                    print(f"   Progress: {progress_data.get('progress', 'Unknown')}")
                else:
                    print(f"⚠️ Progress API returned: {progress_response.status_code}")
            
            return True
        else:
            print(f"❌ Download API returned status code: {response.status_code}")
            print(f"   Response: {response.text[:200]}...")
            return False
            
    except requests.exceptions.Timeout:
        print("⏰ Download API request timed out")
        return False
    except Exception as e:
        print(f"❌ Error testing download API: {e}")
        return False

def main():
    """Main test function"""
    print("🚀 YouTube Downloader Server Test")
    print("=" * 40)
    print(f"⏰ Test started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Run tests
    tests = [
        ("Server Running", test_server_running),
        ("Video Info API", test_video_info_api),
        ("Download API", test_download_api),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"🔄 Running {test_name} test...")
        if test_func():
            passed += 1
        time.sleep(1)  # Brief pause between tests
    
    # Summary
    print("\n" + "=" * 40)
    print(f"📊 Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All tests passed! YouTube Downloader is fully operational.")
        print("🌐 Access the web interface at: http://127.0.0.1:5000")
    elif passed >= total * 0.5:
        print("⚠️ Some tests failed, but basic functionality is working.")
        print("🌐 Try accessing: http://127.0.0.1:5000")
    else:
        print("❌ Multiple tests failed. Server may not be running properly.")
        print("🔧 Check the server logs for errors.")
    
    print("=" * 40)

if __name__ == "__main__":
    main()