#!/usr/bin/env python3
"""
Speed Test for Optimized YouTube Downloader
"""

import time
import requests
import json
from datetime import datetime

def test_optimized_speed():
    """Test the optimized performance"""
    print("🚀 Testing Optimized Performance")
    print("=" * 40)
    
    test_urls = [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://www.youtube.com/watch?v=9bZkp7q19f0",
    ]
    
    total_time = 0
    successful_tests = 0
    
    for i, url in enumerate(test_urls, 1):
        print(f"\n🧪 Speed Test {i}/{len(test_urls)}")
        print(f"URL: {url}")
        
        try:
            start_time = time.time()
            
            response = requests.post('http://127.0.0.1:5000/api/video_info', 
                                   json={'url': url}, 
                                   timeout=30)
            
            end_time = time.time()
            fetch_time = end_time - start_time
            total_time += fetch_time
            
            if response.status_code == 200:
                data = response.json()
                formats_count = len(data.get('formats', []))
                print(f"✅ Success: {fetch_time:.2f}s ({formats_count} formats)")
                successful_tests += 1
            else:
                print(f"❌ Failed: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Error: {str(e)[:50]}...")
    
    if successful_tests > 0:
        avg_time = total_time / successful_tests
        print(f"\n📊 Performance Results:")
        print(f"   Average time: {avg_time:.2f}s")
        print(f"   Success rate: {successful_tests}/{len(test_urls)}")
        
        if avg_time < 3:
            print("   🚀 EXCELLENT: Very fast!")
        elif avg_time < 5:
            print("   ✅ GOOD: Fast enough")
        elif avg_time < 10:
            print("   ⚠️ MODERATE: Could be faster")
        else:
            print("   🐌 SLOW: Needs more optimization")
    
    # Test caching
    print("\n💾 Testing Cache Performance")
    if successful_tests > 0:
        url = test_urls[0]
        start_time = time.time()
        response = requests.post('http://127.0.0.1:5000/api/video_info', 
                               json={'url': url}, 
                               timeout=10)
        cache_time = time.time() - start_time
        
        if response.status_code == 200:
            print(f"✅ Cached response: {cache_time:.2f}s")
            if cache_time < 1:
                print("   🚀 Cache working perfectly!")
            else:
                print("   ⚠️ Cache may not be working")

if __name__ == "__main__":
    test_optimized_speed()
