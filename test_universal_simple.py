#!/usr/bin/env python3
"""
Simple test for universal interface timing
"""

import requests
import time
from datetime import datetime

def test_universal_endpoints():
    """Test universal endpoints with timing"""
    print("🌐 Universal Interface Simple Timing Test")
    print("=" * 60)
    
    base_url = "http://127.0.0.1:5000"
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    
    # Test 1: Page load
    print("📄 Testing page load...")
    try:
        start = time.time()
        response = requests.get(f"{base_url}/universal", timeout=10)
        page_time = time.time() - start
        print(f"✅ Universal page: {page_time:.3f}s (HTTP {response.status_code})")
    except Exception as e:
        print(f"❌ Page load failed: {e}")
        return
    
    # Test 2: YouTube analyze endpoint
    print(f"\n📊 Testing YouTube analyze...")
    try:
        start = time.time()
        response = requests.post(
            f"{base_url}/api/youtube/analyze",
            json={'url': test_url},
            timeout=20
        )
        analyze_time = time.time() - start
        
        if response.status_code == 200:
            data = response.json()
            title = data.get('title', 'Unknown')[:40]
            formats = len(data.get('formats', []))
            print(f"✅ Analyze: {analyze_time:.2f}s")
            print(f"   Title: {title}")
            print(f"   Formats: {formats}")
            
            # Test 3: Download endpoint
            if formats > 0:
                print(f"\n⬇️ Testing download...")
                format_id = data['formats'][0].get('format_id')
                
                try:
                    start = time.time()
                    download_response = requests.post(
                        f"{base_url}/api/youtube/download",
                        json={'url': test_url, 'format_id': format_id},
                        timeout=15
                    )
                    download_start_time = time.time() - start
                    
                    if download_response.status_code == 200:
                        download_data = download_response.json()
                        task_id = download_data.get('task_id')
                        print(f"✅ Download started: {download_start_time:.2f}s")
                        print(f"   Task ID: {task_id}")
                        
                        # Monitor progress briefly
                        if task_id:
                            print("   📊 Monitoring progress...")
                            for i in range(10):  # Check for 20 seconds
                                time.sleep(2)
                                try:
                                    progress_response = requests.get(
                                        f"{base_url}/api/progress/{task_id}",
                                        timeout=5
                                    )
                                    if progress_response.status_code == 200:
                                        progress_data = progress_response.json()
                                        status = progress_data.get('status')
                                        progress = progress_data.get('progress', '')
                                        print(f"      {status}: {progress}")
                                        
                                        if status in ['completed', 'finished', 'failed']:
                                            total_time = analyze_time + download_start_time + (i * 2)
                                            print(f"   🎯 Total time: {total_time:.2f}s")
                                            break
                                except:
                                    pass
                    else:
                        print(f"❌ Download failed: HTTP {download_response.status_code}")
                        print(f"   Response: {download_response.text[:100]}")
                        
                except Exception as e:
                    print(f"❌ Download error: {e}")
            
        else:
            print(f"❌ Analyze failed: HTTP {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            
    except Exception as e:
        print(f"❌ Analyze error: {e}")

def test_regular_endpoints():
    """Test regular endpoints for comparison"""
    print(f"\n🔄 Testing regular endpoints for comparison...")
    
    base_url = "http://127.0.0.1:5000"
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    
    try:
        start = time.time()
        response = requests.post(
            f"{base_url}/api/video_info",
            json={'url': test_url},
            timeout=15
        )
        regular_time = time.time() - start
        
        if response.status_code == 200:
            data = response.json()
            formats = len(data.get('formats', []))
            print(f"✅ Regular video_info: {regular_time:.2f}s ({formats} formats)")
        else:
            print(f"❌ Regular endpoint failed: HTTP {response.status_code}")
            
    except Exception as e:
        print(f"❌ Regular endpoint error: {e}")

if __name__ == "__main__":
    print(f"⏰ Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    test_universal_endpoints()
    test_regular_endpoints()
    print(f"⏰ Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")