#!/usr/bin/env python3
"""
Network Connectivity Fix for YouTube Downloader
Diagnoses and fixes DNS/network issues
"""

import os
import sys
import socket
import subprocess
import time
from datetime import datetime

def print_banner():
    """Print fix banner"""
    print("🌐 Network Connectivity Fix")
    print("=" * 40)
    print(f"⏰ Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

def test_dns_resolution():
    """Test DNS resolution for YouTube domains"""
    print("🔍 Testing DNS Resolution")
    print("-" * 30)
    
    domains = [
        'youtube.com',
        'www.youtube.com',
        'youtubei.googleapis.com',
        'www.googleapis.com',
        'google.com',
        '8.8.8.8'  # Google DNS
    ]
    
    working_domains = []
    failed_domains = []
    
    for domain in domains:
        try:
            print(f"🧪 Testing {domain}...", end=" ")
            
            # Try to resolve the domain
            if domain == '8.8.8.8':
                # For IP, just try to connect
                socket.create_connection((domain, 53), timeout=5).close()
            else:
                socket.gethostbyname(domain)
            
            print("✅ OK")
            working_domains.append(domain)
            
        except Exception as e:
            print(f"❌ Failed: {str(e)[:50]}...")
            failed_domains.append((domain, str(e)))
    
    print(f"\n📊 Results: {len(working_domains)}/{len(domains)} domains working")
    
    if failed_domains:
        print("\n❌ Failed domains:")
        for domain, error in failed_domains:
            print(f"   {domain}: {error[:60]}...")
    
    return len(working_domains) > len(failed_domains)

def test_internet_connectivity():
    """Test basic internet connectivity"""
    print("\n🌍 Testing Internet Connectivity")
    print("-" * 30)
    
    test_hosts = [
        ('8.8.8.8', 53, 'Google DNS'),
        ('1.1.1.1', 53, 'Cloudflare DNS'),
        ('208.67.222.222', 53, 'OpenDNS'),
    ]
    
    working_connections = 0
    
    for host, port, name in test_hosts:
        try:
            print(f"🧪 Testing {name} ({host}:{port})...", end=" ")
            socket.create_connection((host, port), timeout=5).close()
            print("✅ OK")
            working_connections += 1
        except Exception as e:
            print(f"❌ Failed: {str(e)[:30]}...")
    
    print(f"\n📊 Results: {working_connections}/{len(test_hosts)} connections working")
    return working_connections > 0

def flush_dns_cache():
    """Flush DNS cache on Windows"""
    print("\n🔄 Flushing DNS Cache")
    print("-" * 30)
    
    try:
        print("🧹 Flushing Windows DNS cache...")
        result = subprocess.run(['ipconfig', '/flushdns'], 
                              capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("✅ DNS cache flushed successfully")
            return True
        else:
            print(f"⚠️ DNS flush returned code {result.returncode}")
            print(f"   Output: {result.stdout[:100]}...")
            return False
            
    except Exception as e:
        print(f"❌ Failed to flush DNS cache: {e}")
        return False

def reset_network_stack():
    """Reset Windows network stack"""
    print("\n🔧 Resetting Network Stack")
    print("-" * 30)
    
    commands = [
        (['netsh', 'winsock', 'reset'], "Winsock reset"),
        (['netsh', 'int', 'ip', 'reset'], "IP stack reset"),
    ]
    
    success_count = 0
    
    for cmd, description in commands:
        try:
            print(f"🔄 {description}...", end=" ")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            
            if result.returncode == 0:
                print("✅ OK")
                success_count += 1
            else:
                print(f"⚠️ Warning (code {result.returncode})")
                
        except Exception as e:
            print(f"❌ Failed: {str(e)[:30]}...")
    
    if success_count > 0:
        print("\n⚠️ Network stack reset commands executed.")
        print("   You may need to restart your computer for full effect.")
    
    return success_count > 0

def configure_dns_servers():
    """Configure reliable DNS servers"""
    print("\n🔧 Configuring DNS Servers")
    print("-" * 30)
    
    print("💡 Recommended DNS servers:")
    print("   Primary: 8.8.8.8 (Google)")
    print("   Secondary: 1.1.1.1 (Cloudflare)")
    print("   Alternative: 208.67.222.222 (OpenDNS)")
    
    print("\n📋 To manually configure DNS:")
    print("   1. Open Network and Sharing Center")
    print("   2. Click 'Change adapter settings'")
    print("   3. Right-click your network connection")
    print("   4. Select 'Properties'")
    print("   5. Select 'Internet Protocol Version 4 (TCP/IPv4)'")
    print("   6. Click 'Properties'")
    print("   7. Select 'Use the following DNS server addresses'")
    print("   8. Enter: Primary: 8.8.8.8, Secondary: 1.1.1.1")
    
    return True

def test_youtube_specific():
    """Test YouTube-specific connectivity"""
    print("\n📺 Testing YouTube Connectivity")
    print("-" * 30)
    
    youtube_hosts = [
        ('youtube.com', 443),
        ('www.youtube.com', 443),
        ('youtubei.googleapis.com', 443),
    ]
    
    working_hosts = 0
    
    for host, port in youtube_hosts:
        try:
            print(f"🧪 Testing {host}:{port}...", end=" ")
            socket.create_connection((host, port), timeout=10).close()
            print("✅ OK")
            working_hosts += 1
        except Exception as e:
            print(f"❌ Failed: {str(e)[:40]}...")
    
    print(f"\n📊 Results: {working_hosts}/{len(youtube_hosts)} YouTube hosts reachable")
    return working_hosts > 0

def check_firewall_antivirus():
    """Check for firewall/antivirus interference"""
    print("\n🛡️ Checking Security Software")
    print("-" * 30)
    
    print("🔍 Common causes of DNS/network issues:")
    print("   • Windows Firewall blocking connections")
    print("   • Antivirus software with web protection")
    print("   • VPN software interfering with DNS")
    print("   • Proxy settings blocking connections")
    print("   • Corporate network restrictions")
    
    print("\n💡 Troubleshooting steps:")
    print("   1. Temporarily disable Windows Firewall")
    print("   2. Disable antivirus web protection")
    print("   3. Disconnect from VPN if connected")
    print("   4. Check proxy settings in browser")
    print("   5. Try from different network (mobile hotspot)")
    
    return True

def create_network_test_script():
    """Create a simple network test script"""
    print("\n📝 Creating Network Test Script")
    print("-" * 30)
    
    script_content = '''@echo off
echo Testing Network Connectivity...
echo.

echo Testing basic connectivity:
ping -n 2 8.8.8.8
echo.

echo Testing YouTube domains:
nslookup youtube.com
echo.
nslookup www.youtube.com
echo.

echo Testing with different DNS:
nslookup youtube.com 8.8.8.8
echo.

echo Network configuration:
ipconfig /all
echo.

pause
'''
    
    try:
        with open('network_test.bat', 'w') as f:
            f.write(script_content)
        print("✅ Created network_test.bat")
        print("   Run this script to test network connectivity")
        return True
    except Exception as e:
        print(f"❌ Failed to create test script: {e}")
        return False

def suggest_solutions():
    """Suggest solutions based on test results"""
    print("\n💡 Recommended Solutions")
    print("-" * 30)
    
    solutions = [
        "🔄 Restart your router/modem",
        "🔧 Change DNS servers to 8.8.8.8 and 1.1.1.1",
        "🧹 Flush DNS cache: ipconfig /flushdns",
        "🛡️ Temporarily disable firewall/antivirus",
        "🌐 Try connecting to different network",
        "🔄 Restart network adapter",
        "💻 Restart computer",
        "📞 Contact your ISP if issues persist"
    ]
    
    for i, solution in enumerate(solutions, 1):
        print(f"   {i}. {solution}")
    
    return True

def main():
    """Main network fix function"""
    print_banner()
    
    # Run network tests
    tests = [
        ("Internet Connectivity", test_internet_connectivity),
        ("DNS Resolution", test_dns_resolution),
        ("YouTube Connectivity", test_youtube_specific),
    ]
    
    passed_tests = 0
    total_tests = len(tests)
    
    for test_name, test_func in tests:
        print(f"🔄 Running {test_name} test...")
        if test_func():
            passed_tests += 1
        time.sleep(1)
    
    # Run fixes if needed
    if passed_tests < total_tests:
        print("\n🔧 Attempting Fixes")
        print("=" * 40)
        
        fixes = [
            ("Flush DNS Cache", flush_dns_cache),
            ("Configure DNS", configure_dns_servers),
            ("Check Security Software", check_firewall_antivirus),
            ("Create Test Script", create_network_test_script),
        ]
        
        for fix_name, fix_func in fixes:
            print(f"🔄 {fix_name}...")
            fix_func()
            time.sleep(1)
        
        # Suggest additional solutions
        suggest_solutions()
    
    # Final summary
    print("\n" + "=" * 40)
    print("📊 Network Diagnostic Summary")
    print("=" * 40)
    print(f"Tests passed: {passed_tests}/{total_tests}")
    
    if passed_tests == total_tests:
        print("✅ Network connectivity looks good!")
        print("   The DNS issues may be temporary.")
        print("   Try running the YouTube Downloader again.")
    elif passed_tests > 0:
        print("⚠️ Partial network connectivity detected.")
        print("   Some fixes have been applied.")
        print("   Try the suggested solutions above.")
    else:
        print("❌ Network connectivity issues detected.")
        print("   Follow the troubleshooting steps above.")
        print("   Consider contacting your network administrator.")
    
    print("\n🔄 After applying fixes, test with:")
    print("   python quick_test.py")
    print("=" * 40)

if __name__ == "__main__":
    main()