#!/usr/bin/env python3
"""
Simple script to check if the server is running
"""
import requests
import sys

def check_server():
    try:
        response = requests.get('http://127.0.0.1:5000', timeout=5)
        if response.status_code == 200:
            print("✅ Server is running successfully!")
            print(f"   Status Code: {response.status_code}")
            print(f"   Server: Waitress (Production)")
            print(f"   URL: http://127.0.0.1:5000")
            return True
        else:
            print(f"⚠️  Server responded with status code: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Server is not running or not accessible")
        print("   Try running: start_production.bat")
        return False
    except requests.exceptions.Timeout:
        print("⏱️  Server is taking too long to respond")
        return False
    except Exception as e:
        print(f"❌ Error checking server: {e}")
        return False

if __name__ == "__main__":
    print("Checking YouTube Downloader server status...")
    print("-" * 50)
    
    if check_server():
        sys.exit(0)
    else:
        sys.exit(1)