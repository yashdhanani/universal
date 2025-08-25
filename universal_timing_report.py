#!/usr/bin/env python3
"""
Comprehensive timing report for Universal Interface
"""

import requests
import time
import json
from datetime import datetime

def test_universal_timing_comprehensive():
    """Test all aspects of universal interface timing"""
    print("🌐 Universal Interface Comprehensive Timing Report")
    print("=" * 70)
    print(f"⏰ Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    base_url = "http://127.0.0.1:5000"
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    
    results = {}
    
    # 1. Page Load Test
    print("\n📄 1. Universal Page Load Test")
    print("-" * 40)
    try:
        start = time.time()
        response = requests.get(f"{base_url}/universal", timeout=10)
        page_load_time = time.time() - start
        
        if response.status_code == 200:
            page_size = len(response.content)
            print(f"✅ Page loaded: {page_load_time:.3f}s")
            print(f"📄 Page size: {page_size:,} bytes")
            results['page_load'] = {
                'time': page_load_time,
                'size': page_size,
                'status': 'success'
            }
        else:
            print(f"❌ Page load failed: HTTP {response.status_code}")
            results['page_load'] = {'status': 'failed', 'code': response.status_code}
    except Exception as e:
        print(f"❌ Page load error: {e}")
        results['page_load'] = {'status': 'error', 'error': str(e)}
    
    # 2. Link Analysis Test (First Request)
    print("\n📊 2. Link Analysis Test (First Request)")
    print("-" * 40)
    try:
        start = time.time()
        response = requests.post(
            f"{base_url}/api/youtube/analyze",
            json={'url': test_url},
            timeout=25
        )
        first_analyze_time = time.time() - start
        
        if response.status_code == 200:
            data = response.json()
            title = data.get('title', 'Unknown')[:40]
            formats = len(data.get('formats', []))
            print(f"✅ First analysis: {first_analyze_time:.2f}s")
            print(f"📹 Title: {title}")
            print(f"🎬 Formats: {formats}")
            
            results['first_analyze'] = {
                'time': first_analyze_time,
                'title': title,
                'formats': formats,
                'status': 'success'
            }
            
            # Store format for download test
            test_format = None
            if formats > 0:
                # Find smallest format for testing
                for f in data['formats']:
                    if f.get('filesize_mb') and f.get('filesize_mb') < 10:
                        test_format = f
                        break
                if not test_format:
                    test_format = data['formats'][-1]  # Use last format
                    
        else:
            print(f"❌ First analysis failed: HTTP {response.status_code}")
            results['first_analyze'] = {'status': 'failed', 'code': response.status_code}
            test_format = None
            
    except Exception as e:
        print(f"❌ First analysis error: {e}")
        results['first_analyze'] = {'status': 'error', 'error': str(e)}
        test_format = None
    
    # 3. Cached Analysis Test
    print("\n⚡ 3. Cached Analysis Test")
    print("-" * 40)
    try:
        start = time.time()
        response = requests.post(
            f"{base_url}/api/youtube/analyze",
            json={'url': test_url},
            timeout=10
        )
        cached_analyze_time = time.time() - start
        
        if response.status_code == 200:
            print(f"✅ Cached analysis: {cached_analyze_time:.3f}s")
            speedup = first_analyze_time / cached_analyze_time if cached_analyze_time > 0 else 0
            print(f"🚀 Speedup: {speedup:.0f}x faster")
            
            results['cached_analyze'] = {
                'time': cached_analyze_time,
                'speedup': speedup,
                'status': 'success'
            }
        else:
            print(f"❌ Cached analysis failed: HTTP {response.status_code}")
            results['cached_analyze'] = {'status': 'failed', 'code': response.status_code}
            
    except Exception as e:
        print(f"❌ Cached analysis error: {e}")
        results['cached_analyze'] = {'status': 'error', 'error': str(e)}
    
    # 4. Download Test
    print("\n⬇️ 4. Download Test")
    print("-" * 40)
    if test_format:
        try:
            print(f"🎯 Testing format: {test_format.get('quality')} ({test_format.get('filesize_mb', 'unknown')} MB)")
            
            start = time.time()
            download_response = requests.post(
                f"{base_url}/api/youtube/download",
                json={'url': test_url, 'format_id': test_format.get('format_id')},
                timeout=15
            )
            download_init_time = time.time() - start
            
            if download_response.status_code == 200:
                download_data = download_response.json()
                task_id = download_data.get('task_id')
                print(f"✅ Download initiated: {download_init_time:.2f}s")
                print(f"📋 Task ID: {task_id}")
                
                # Monitor download progress
                if task_id:
                    download_result = monitor_download_detailed(base_url, task_id)
                    results['download'] = {
                        'init_time': download_init_time,
                        'total_time': download_result.get('total_time', 0),
                        'status': download_result.get('status'),
                        'format': test_format.get('quality'),
                        'filesize_mb': test_format.get('filesize_mb')
                    }
                else:
                    results['download'] = {'status': 'no_task_id'}
            else:
                print(f"❌ Download failed: HTTP {download_response.status_code}")
                print(f"   Response: {download_response.text[:100]}")
                results['download'] = {'status': 'failed', 'code': download_response.status_code}
                
        except Exception as e:
            print(f"❌ Download error: {e}")
            results['download'] = {'status': 'error', 'error': str(e)}
    else:
        print("⚠️ Skipping download test - no format available")
        results['download'] = {'status': 'skipped', 'reason': 'no_format'}
    
    # 5. Comparison with Regular API
    print("\n🔄 5. Regular API Comparison")
    print("-" * 40)
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
            print(f"✅ Regular API: {regular_time:.3f}s ({formats} formats)")
            
            results['regular_api'] = {
                'time': regular_time,
                'formats': formats,
                'status': 'success'
            }
        else:
            print(f"❌ Regular API failed: HTTP {response.status_code}")
            results['regular_api'] = {'status': 'failed', 'code': response.status_code}
            
    except Exception as e:
        print(f"❌ Regular API error: {e}")
        results['regular_api'] = {'status': 'error', 'error': str(e)}
    
    return results

def monitor_download_detailed(base_url, task_id, max_wait=60):
    """Monitor download with detailed timing"""
    print(f"   📊 Monitoring download progress...")
    
    start_time = time.time()
    last_progress = ""
    status_changes = []
    
    while time.time() - start_time < max_wait:
        try:
            progress_response = requests.get(
                f"{base_url}/api/progress/{task_id}",
                timeout=5
            )
            
            if progress_response.status_code == 200:
                progress_data = progress_response.json()
                status = progress_data.get('status')
                progress = progress_data.get('progress', '')
                elapsed = time.time() - start_time
                
                if progress != last_progress:
                    print(f"      📈 {status}: {progress} ({elapsed:.1f}s)")
                    status_changes.append({
                        'time': elapsed,
                        'status': status,
                        'progress': progress
                    })
                    last_progress = progress
                
                if status in ['completed', 'finished']:
                    filename = progress_data.get('filename')
                    print(f"   ✅ Download completed: {elapsed:.2f}s")
                    if filename:
                        print(f"   📁 File: {filename}")
                    
                    return {
                        'status': 'completed',
                        'total_time': elapsed,
                        'filename': filename,
                        'status_changes': status_changes
                    }
                elif status == 'failed':
                    print(f"   ❌ Download failed: {elapsed:.2f}s")
                    return {
                        'status': 'failed',
                        'total_time': elapsed,
                        'status_changes': status_changes
                    }
            
            time.sleep(2)
            
        except Exception as e:
            print(f"      ⚠️ Progress check error: {str(e)[:30]}...")
            time.sleep(2)
    
    print(f"   ⏰ Download monitoring timed out after {max_wait}s")
    return {
        'status': 'timeout',
        'total_time': max_wait,
        'status_changes': status_changes
    }

def print_summary_report(results):
    """Print comprehensive summary report"""
    print("\n" + "=" * 70)
    print("📊 UNIVERSAL INTERFACE TIMING SUMMARY")
    print("=" * 70)
    
    # Page Load
    if 'page_load' in results and results['page_load']['status'] == 'success':
        time_val = results['page_load']['time']
        print(f"📄 Page Load: {time_val:.3f}s")
        if time_val < 0.1:
            print("   🚀 EXCELLENT: Lightning fast")
        elif time_val < 0.5:
            print("   ✅ GOOD: Very fast")
        else:
            print("   ⚠️ SLOW: Could be improved")
    
    # Link Analysis
    if 'first_analyze' in results and results['first_analyze']['status'] == 'success':
        first_time = results['first_analyze']['time']
        print(f"\n📊 Link Analysis (First): {first_time:.2f}s")
        
        if 'cached_analyze' in results and results['cached_analyze']['status'] == 'success':
            cached_time = results['cached_analyze']['time']
            speedup = results['cached_analyze']['speedup']
            print(f"⚡ Link Analysis (Cached): {cached_time:.3f}s ({speedup:.0f}x faster)")
        
        if first_time < 5:
            print("   🚀 EXCELLENT: Very fast analysis")
        elif first_time < 15:
            print("   ✅ GOOD: Acceptable analysis time")
        else:
            print("   ⚠️ SLOW: Analysis could be improved")
    
    # Download Performance
    if 'download' in results:
        download = results['download']
        if download['status'] == 'completed':
            init_time = download.get('init_time', 0)
            total_time = download.get('total_time', 0)
            print(f"\n⬇️ Download Performance:")
            print(f"   Initiation: {init_time:.2f}s")
            print(f"   Total time: {total_time:.2f}s")
            print(f"   Format: {download.get('format', 'unknown')}")
            
            if total_time < 30:
                print("   🚀 EXCELLENT: Very fast download")
            elif total_time < 60:
                print("   ✅ GOOD: Fast download")
            else:
                print("   ⚠️ SLOW: Download could be improved")
        else:
            print(f"\n⬇️ Download: {download['status']}")
    
    # API Comparison
    if ('first_analyze' in results and 'regular_api' in results and 
        results['first_analyze']['status'] == 'success' and 
        results['regular_api']['status'] == 'success'):
        
        universal_time = results['first_analyze']['time']
        regular_time = results['regular_api']['time']
        
        print(f"\n🔄 API Comparison:")
        print(f"   Universal API: {universal_time:.2f}s")
        print(f"   Regular API: {regular_time:.3f}s")
        
        if universal_time < regular_time * 2:
            print("   ✅ Universal API performance is competitive")
        else:
            print("   ⚠️ Universal API is slower than regular API")
    
    print(f"\n🎯 Overall Assessment:")
    
    # Count successful operations
    successful_ops = sum(1 for key, result in results.items() 
                        if isinstance(result, dict) and result.get('status') == 'success')
    total_ops = len([k for k in results.keys() if k != 'download' or results[k].get('status') != 'skipped'])
    
    print(f"   Success rate: {successful_ops}/{total_ops} operations")
    
    if successful_ops == total_ops:
        print("   🚀 EXCELLENT: All operations successful")
    elif successful_ops >= total_ops * 0.8:
        print("   ✅ GOOD: Most operations successful")
    else:
        print("   ⚠️ ISSUES: Some operations failed")

if __name__ == "__main__":
    results = test_universal_timing_comprehensive()
    print_summary_report(results)
    print(f"\n⏰ Test completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")