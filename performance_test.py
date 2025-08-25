#!/usr/bin/env python3
"""
Comprehensive performance test and optimization
"""

import requests
import time
import threading
from datetime import datetime
import json

def test_video_info_performance():
    """Test video info fetch performance with multiple URLs"""
    print("🚀 Video Info Performance Test")
    print("=" * 60)
    
    test_urls = [
        'https://www.youtube.com/watch?v=dQw4w9WgXcQ',  # Rick Roll
        'https://www.youtube.com/watch?v=9bZkp7q19f0',  # PSY - Gangnam Style
        'https://www.youtube.com/watch?v=kJQP7kiw5Fk',  # Despacito
        'https://www.youtube.com/watch?v=fJ9rUzIMcZQ',  # Bohemian Rhapsody
        'https://www.youtube.com/watch?v=YQHsXMglC9A',  # Hello - Adele
    ]
    
    results = []
    
    for i, url in enumerate(test_urls, 1):
        print(f"\n🔄 Test {i}/5: {url.split('=')[1]}")
        
        try:
            start_time = time.time()
            
            response = requests.post(
                'http://127.0.0.1:5000/api/video_info',
                json={'url': url},
                timeout=30
            )
            
            end_time = time.time()
            fetch_time = end_time - start_time
            
            if response.status_code == 200:
                data = response.json()
                title = data.get('title', 'Unknown')[:40]
                formats_count = len(data.get('formats', []))
                
                print(f"   ✅ Success: {fetch_time:.2f}s")
                print(f"   📹 Title: {title}")
                print(f"   🎬 Formats: {formats_count}")
                
                results.append({
                    'url': url,
                    'time': fetch_time,
                    'success': True,
                    'title': title,
                    'formats': formats_count
                })
            else:
                print(f"   ❌ Failed: HTTP {response.status_code}")
                results.append({
                    'url': url,
                    'time': fetch_time,
                    'success': False,
                    'error': f"HTTP {response.status_code}"
                })
                
        except Exception as e:
            print(f"   ❌ Error: {str(e)[:50]}...")
            results.append({
                'url': url,
                'time': 0,
                'success': False,
                'error': str(e)[:50]
            })
    
    return results

def test_concurrent_requests():
    """Test concurrent video info requests"""
    print("\n🔀 Concurrent Requests Test")
    print("=" * 60)
    
    test_url = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
    num_concurrent = 3
    results = []
    
    def fetch_video_info(thread_id):
        try:
            start_time = time.time()
            
            response = requests.post(
                'http://127.0.0.1:5000/api/video_info',
                json={'url': test_url},
                timeout=30
            )
            
            end_time = time.time()
            fetch_time = end_time - start_time
            
            results.append({
                'thread_id': thread_id,
                'time': fetch_time,
                'success': response.status_code == 200,
                'status_code': response.status_code
            })
            
            print(f"   Thread {thread_id}: {fetch_time:.2f}s (HTTP {response.status_code})")
            
        except Exception as e:
            results.append({
                'thread_id': thread_id,
                'time': 0,
                'success': False,
                'error': str(e)[:50]
            })
            print(f"   Thread {thread_id}: Error - {str(e)[:50]}")
    
    print(f"🔄 Starting {num_concurrent} concurrent requests...")
    start_time = time.time()
    
    threads = []
    for i in range(num_concurrent):
        thread = threading.Thread(target=fetch_video_info, args=(i+1,))
        threads.append(thread)
        thread.start()
    
    for thread in threads:
        thread.join()
    
    end_time = time.time()
    total_time = end_time - start_time
    
    print(f"\n📊 Concurrent Test Results:")
    print(f"   Total time: {total_time:.2f}s")
    print(f"   Average per request: {total_time/num_concurrent:.2f}s")
    
    successful = sum(1 for r in results if r['success'])
    print(f"   Success rate: {successful}/{num_concurrent}")
    
    return results

def test_download_performance():
    """Test actual download performance"""
    print("\n⬇️ Download Performance Test")
    print("=" * 60)
    
    test_url = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
    
    try:
        # First get video info
        print("🔄 Getting video info...")
        start_time = time.time()
        
        response = requests.post(
            'http://127.0.0.1:5000/api/video_info',
            json={'url': test_url},
            timeout=30
        )
        
        info_time = time.time() - start_time
        
        if response.status_code != 200:
            print(f"❌ Failed to get video info: HTTP {response.status_code}")
            return None
        
        data = response.json()
        formats = data.get('formats', [])
        
        if not formats:
            print("❌ No formats available")
            return None
        
        # Find a small format for testing (audio or low quality)
        test_format = None
        for f in formats:
            if (f.get('filesize_mb', 0) and f.get('filesize_mb') < 5) or 'audio' in f.get('quality', '').lower():
                test_format = f
                break
        
        if not test_format:
            test_format = formats[0]  # Use first format as fallback
        
        print(f"✅ Video info: {info_time:.2f}s")
        print(f"🎯 Testing format: {test_format.get('quality')} ({test_format.get('filesize_mb', 'unknown')} MB)")
        
        # Start download
        print("🔄 Starting download...")
        download_start = time.time()
        
        download_response = requests.post(
            'http://127.0.0.1:5000/api/download',
            json={
                'url': test_url,
                'format_id': test_format.get('format_id')
            },
            timeout=10
        )
        
        if download_response.status_code != 200:
            print(f"❌ Failed to start download: HTTP {download_response.status_code}")
            return None
        
        download_data = download_response.json()
        task_id = download_data.get('task_id')
        
        if not task_id:
            print("❌ No task ID received")
            return None
        
        print(f"✅ Download started: {task_id}")
        
        # Monitor progress for 30 seconds max
        max_wait = 30
        elapsed = 0
        last_progress = ""
        
        while elapsed < max_wait:
            time.sleep(2)
            elapsed += 2
            
            try:
                progress_response = requests.get(
                    f'http://127.0.0.1:5000/api/progress/{task_id}',
                    timeout=5
                )
                
                if progress_response.status_code == 200:
                    progress_data = progress_response.json()
                    status = progress_data.get('status')
                    progress = progress_data.get('progress', '')
                    
                    if progress != last_progress:
                        print(f"   📊 {status}: {progress}")
                        last_progress = progress
                    
                    if status in ['completed', 'failed']:
                        total_time = time.time() - download_start
                        print(f"✅ Download {status}: {total_time:.2f}s total")
                        
                        if status == 'completed':
                            filename = progress_data.get('filename')
                            if filename:
                                print(f"📁 File: {filename}")
                        
                        return {
                            'info_time': info_time,
                            'download_time': total_time,
                            'total_time': info_time + total_time,
                            'status': status,
                            'format': test_format
                        }
                
            except Exception as e:
                print(f"   ⚠️ Progress check error: {str(e)[:50]}")
        
        print(f"⏰ Download test timed out after {max_wait}s")
        return {
            'info_time': info_time,
            'download_time': max_wait,
            'total_time': info_time + max_wait,
            'status': 'timeout',
            'format': test_format
        }
        
    except Exception as e:
        print(f"❌ Download test failed: {str(e)[:100]}")
        return None

def main():
    """Main performance test function"""
    print("🚀 YouTube Downloader Performance Analysis")
    print("=" * 80)
    print(f"⏰ Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Test 1: Video info performance
    info_results = test_video_info_performance()
    
    # Test 2: Concurrent requests
    concurrent_results = test_concurrent_requests()
    
    # Test 3: Download performance (optional - can be slow)
    print("\n❓ Run download test? (This may take 30+ seconds)")
    print("   Press Enter to skip, or type 'y' to run:")
    user_input = input().strip().lower()
    
    download_result = None
    if user_input == 'y':
        download_result = test_download_performance()
    else:
        print("⏭️ Skipping download test")
    
    # Final analysis
    print("\n" + "=" * 80)
    print("📊 PERFORMANCE ANALYSIS SUMMARY")
    print("=" * 80)
    
    # Video info analysis
    successful_info = [r for r in info_results if r['success']]
    if successful_info:
        avg_time = sum(r['time'] for r in successful_info) / len(successful_info)
        min_time = min(r['time'] for r in successful_info)
        max_time = max(r['time'] for r in successful_info)
        
        print(f"📹 Video Info Performance:")
        print(f"   Success rate: {len(successful_info)}/{len(info_results)}")
        print(f"   Average time: {avg_time:.2f}s")
        print(f"   Range: {min_time:.2f}s - {max_time:.2f}s")
        
        if avg_time < 5:
            print("   🚀 EXCELLENT: Very fast response times")
        elif avg_time < 10:
            print("   ✅ GOOD: Acceptable response times")
        elif avg_time < 15:
            print("   ⚠️ SLOW: Could be improved")
        else:
            print("   ❌ VERY SLOW: Needs optimization")
    
    # Concurrent analysis
    successful_concurrent = [r for r in concurrent_results if r['success']]
    if successful_concurrent:
        concurrent_avg = sum(r['time'] for r in successful_concurrent) / len(successful_concurrent)
        print(f"\n🔀 Concurrent Performance:")
        print(f"   Success rate: {len(successful_concurrent)}/{len(concurrent_results)}")
        print(f"   Average time: {concurrent_avg:.2f}s")
        
        if concurrent_avg < avg_time * 1.2:
            print("   ✅ Good concurrent handling")
        else:
            print("   ⚠️ Concurrent requests are slower")
    
    # Download analysis
    if download_result:
        print(f"\n⬇️ Download Performance:")
        print(f"   Info fetch: {download_result['info_time']:.2f}s")
        print(f"   Download: {download_result['download_time']:.2f}s")
        print(f"   Total: {download_result['total_time']:.2f}s")
        print(f"   Status: {download_result['status']}")
    
    # Recommendations
    print(f"\n💡 OPTIMIZATION RECOMMENDATIONS:")
    if avg_time > 10:
        print("   🔧 Consider implementing format caching")
        print("   🔧 Reduce format processing overhead")
        print("   🔧 Use faster yt-dlp client configurations")
    
    if len(successful_info) < len(info_results):
        print("   🛠️ Improve error handling and retry logic")
    
    print("   ⚡ Current optimizations active:")
    print("     • Minimal yt-dlp configuration")
    print("     • Single android client")
    print("     • Reduced retries and timeouts")
    print("     • Fast format processing")
    
    print(f"\n⏰ Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()