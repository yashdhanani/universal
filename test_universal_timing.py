#!/usr/bin/env python3
"""
Test timing for universal interface at /universal
"""

import requests
import time
import json
from datetime import datetime

def test_universal_interface():
    """Test the universal interface timing"""
    print("🌐 Universal Interface Timing Test")
    print("=" * 60)
    print(f"⏰ Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    base_url = "http://127.0.0.1:5000"
    
    # Test URLs for different platforms
    test_cases = [
        {
            'name': 'YouTube - Rick Roll',
            'url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
            'platform': 'youtube'
        },
        {
            'name': 'YouTube - Short Video',
            'url': 'https://www.youtube.com/watch?v=9bZkp7q19f0',
            'platform': 'youtube'
        }
    ]
    
    results = []
    
    for test_case in test_cases:
        print(f"\n🔄 Testing: {test_case['name']}")
        print(f"   URL: {test_case['url']}")
        
        # Test 1: Analyze (fetch link info)
        print("   📊 Step 1: Analyzing link...")
        analyze_start = time.time()
        
        try:
            analyze_response = requests.post(
                f"{base_url}/api/{test_case['platform']}/analyze",
                json={'url': test_case['url']},
                timeout=30
            )
            
            analyze_time = time.time() - analyze_start
            
            if analyze_response.status_code == 200:
                analyze_data = analyze_response.json()
                title = analyze_data.get('title', 'Unknown')[:40]
                formats = analyze_data.get('formats', [])
                
                print(f"   ✅ Analysis: {analyze_time:.2f}s")
                print(f"   📹 Title: {title}")
                print(f"   🎬 Formats: {len(formats)}")
                
                if formats:
                    # Test 2: Download (start download)
                    print("   ⬇️ Step 2: Starting download...")
                    
                    # Find a small format for testing
                    test_format = None
                    for f in formats:
                        if f.get('filesize_mb') and f.get('filesize_mb') < 10:
                            test_format = f
                            break
                    
                    if not test_format and formats:
                        test_format = formats[-1]  # Use last format
                    
                    if test_format:
                        download_start = time.time()
                        
                        try:
                            download_response = requests.post(
                                f"{base_url}/api/{test_case['platform']}/download",
                                json={
                                    'url': test_case['url'],
                                    'format_id': test_format.get('format_id')
                                },
                                timeout=15
                            )
                            
                            if download_response.status_code == 200:
                                download_data = download_response.json()
                                task_id = download_data.get('task_id')
                                
                                print(f"   ✅ Download started: {task_id}")
                                print(f"   🎯 Format: {test_format.get('quality')} ({test_format.get('filesize_mb', 'unknown')} MB)")
                                
                                # Monitor download progress
                                download_result = monitor_download_progress(base_url, task_id, max_wait=60)
                                
                                total_download_time = time.time() - download_start
                                
                                results.append({
                                    'name': test_case['name'],
                                    'url': test_case['url'],
                                    'analyze_time': analyze_time,
                                    'download_time': total_download_time,
                                    'total_time': analyze_time + total_download_time,
                                    'formats_count': len(formats),
                                    'download_status': download_result.get('status') if download_result else 'unknown',
                                    'success': True
                                })
                                
                            else:
                                print(f"   ❌ Download failed: HTTP {download_response.status_code}")
                                results.append({
                                    'name': test_case['name'],
                                    'analyze_time': analyze_time,
                                    'download_time': 0,
                                    'total_time': analyze_time,
                                    'success': False,
                                    'error': f"Download HTTP {download_response.status_code}"
                                })
                                
                        except Exception as e:
                            print(f"   ❌ Download error: {str(e)[:50]}...")
                            results.append({
                                'name': test_case['name'],
                                'analyze_time': analyze_time,
                                'download_time': 0,
                                'total_time': analyze_time,
                                'success': False,
                                'error': str(e)[:50]
                            })
                    else:
                        print("   ⚠️ No suitable format found for download test")
                        results.append({
                            'name': test_case['name'],
                            'analyze_time': analyze_time,
                            'download_time': 0,
                            'total_time': analyze_time,
                            'success': False,
                            'error': 'No suitable format'
                        })
                else:
                    print("   ⚠️ No formats available")
                    results.append({
                        'name': test_case['name'],
                        'analyze_time': analyze_time,
                        'download_time': 0,
                        'total_time': analyze_time,
                        'success': False,
                        'error': 'No formats'
                    })
                    
            else:
                print(f"   ❌ Analysis failed: HTTP {analyze_response.status_code}")
                results.append({
                    'name': test_case['name'],
                    'analyze_time': analyze_time,
                    'download_time': 0,
                    'total_time': analyze_time,
                    'success': False,
                    'error': f"Analysis HTTP {analyze_response.status_code}"
                })
                
        except Exception as e:
            analyze_time = time.time() - analyze_start
            print(f"   ❌ Analysis error: {str(e)[:50]}...")
            results.append({
                'name': test_case['name'],
                'analyze_time': analyze_time,
                'download_time': 0,
                'total_time': analyze_time,
                'success': False,
                'error': str(e)[:50]
            })
    
    return results

def monitor_download_progress(base_url, task_id, max_wait=60):
    """Monitor download progress and return final status"""
    print(f"   📊 Monitoring progress for task: {task_id}")
    
    start_time = time.time()
    last_progress = ""
    
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
                
                if progress != last_progress:
                    print(f"      📈 {status}: {progress}")
                    last_progress = progress
                
                if status in ['completed', 'failed', 'finished']:
                    elapsed = time.time() - start_time
                    print(f"   ✅ Final status: {status} ({elapsed:.2f}s)")
                    
                    result = {
                        'status': status,
                        'elapsed': elapsed,
                        'progress': progress
                    }
                    
                    if status in ['completed', 'finished']:
                        filename = progress_data.get('filename')
                        if filename:
                            print(f"   📁 File: {filename}")
                            result['filename'] = filename
                    
                    return result
            
            time.sleep(2)
            
        except Exception as e:
            print(f"      ⚠️ Progress check error: {str(e)[:30]}...")
            time.sleep(2)
    
    print(f"   ⏰ Progress monitoring timed out after {max_wait}s")
    return {'status': 'timeout', 'elapsed': max_wait}

def test_universal_page_load():
    """Test universal page load time"""
    print("\n🌐 Universal Page Load Test")
    print("=" * 40)
    
    try:
        start_time = time.time()
        response = requests.get("http://127.0.0.1:5000/universal", timeout=10)
        load_time = time.time() - start_time
        
        if response.status_code == 200:
            page_size = len(response.content)
            print(f"✅ Page loaded: {load_time:.3f}s")
            print(f"📄 Page size: {page_size:,} bytes")
            return load_time
        else:
            print(f"❌ Page load failed: HTTP {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ Page load error: {str(e)[:50]}...")
        return None

def main():
    """Main test function"""
    print("🌐 Universal Interface Comprehensive Timing Test")
    print("=" * 80)
    
    # Test 1: Page load time
    page_load_time = test_universal_page_load()
    
    # Test 2: API functionality timing
    api_results = test_universal_interface()
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 UNIVERSAL INTERFACE TIMING SUMMARY")
    print("=" * 80)
    
    if page_load_time:
        print(f"🌐 Page Load Time: {page_load_time:.3f}s")
        if page_load_time < 0.5:
            print("   🚀 EXCELLENT: Very fast page load")
        elif page_load_time < 1.0:
            print("   ✅ GOOD: Fast page load")
        else:
            print("   ⚠️ SLOW: Could be improved")
    
    if api_results:
        successful_tests = [r for r in api_results if r['success']]
        
        if successful_tests:
            avg_analyze = sum(r['analyze_time'] for r in successful_tests) / len(successful_tests)
            avg_download = sum(r.get('download_time', 0) for r in successful_tests) / len(successful_tests)
            avg_total = sum(r['total_time'] for r in successful_tests) / len(successful_tests)
            
            print(f"\n📊 API Performance:")
            print(f"   Success rate: {len(successful_tests)}/{len(api_results)}")
            print(f"   Average analyze time: {avg_analyze:.2f}s")
            print(f"   Average download time: {avg_download:.2f}s")
            print(f"   Average total time: {avg_total:.2f}s")
            
            if avg_analyze < 1:
                print("   🚀 EXCELLENT: Very fast link analysis")
            elif avg_analyze < 5:
                print("   ✅ GOOD: Fast link analysis")
            else:
                print("   ⚠️ SLOW: Link analysis could be improved")
        
        # Individual results
        print(f"\n📋 Individual Test Results:")
        for result in api_results:
            status = "✅" if result['success'] else "❌"
            print(f"   {status} {result['name']}")
            print(f"      Analyze: {result['analyze_time']:.2f}s")
            if 'download_time' in result and result['download_time'] > 0:
                print(f"      Download: {result['download_time']:.2f}s")
                print(f"      Total: {result['total_time']:.2f}s")
            if not result['success'] and 'error' in result:
                print(f"      Error: {result['error']}")
    
    print(f"\n⏰ Test completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()