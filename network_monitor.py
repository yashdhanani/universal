#!/usr/bin/env python3
"""
Network Monitor for YouTube Downloader
Monitors network connectivity and provides alerts
"""

import time
import socket
import subprocess
from datetime import datetime

def test_connectivity():
    """Test basic connectivity"""
    hosts = [
        ('8.8.8.8', 53),
        ('youtube.com', 443),
        ('www.youtube.com', 443)
    ]
    
    working = 0
    for host, port in hosts:
        try:
            socket.create_connection((host, port), timeout=5).close()
            working += 1
        except:
            pass
    
    return working, len(hosts)

def main():
    """Main monitoring loop"""
    print("🌐 Network Monitor Started")
    print("Press Ctrl+C to stop")
    print("-" * 30)
    
    consecutive_failures = 0
    
    while True:
        try:
            working, total = test_connectivity()
            timestamp = datetime.now().strftime('%H:%M:%S')
            
            if working == total:
                print(f"[{timestamp}] ✅ Network OK ({working}/{total})")
                consecutive_failures = 0
            else:
                consecutive_failures += 1
                print(f"[{timestamp}] ⚠️ Network Issues ({working}/{total}) - Failure #{consecutive_failures}")
                
                if consecutive_failures >= 3:
                    print(f"[{timestamp}] 🚨 ALERT: Network unstable for {consecutive_failures} checks")
                    # Could add email/notification here
            
            time.sleep(30)  # Check every 30 seconds
            
        except KeyboardInterrupt:
            print("\n🛑 Network monitor stopped")
            break
        except Exception as e:
            print(f"Monitor error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
