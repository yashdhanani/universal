#!/usr/bin/env python3
"""
YouTube Downloader Troubleshooting Script
Diagnoses and fixes common issues with YouTube downloading
"""

import os
import sys
import subprocess
import json
import yt_dlp
from datetime import datetime

def print_header(title):
    """Print a formatted header"""
    print(f"\n{'='*60}")
    print(f"🔍 {title}")
    print(f"{'='*60}")

def print_section(title):
    """Print a formatted section"""
    print(f"\n📋 {title}")
    print("-" * 40)

def run_command(cmd, timeout=30):
    """Run a command with timeout"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out"
    except Exception as e:
        return False, "", str(e)

def check_python_version():
    """Check Python version"""
    print_section("Python Version Check")
    version = sys.version
    print(f"Python version: {version}")
    
    major, minor = sys.version_info[:2]
    if major >= 3 and minor >= 8:
        print("✅ Python version is compatible")
        return True
    else:
        print("❌ Python version is too old. Requires Python 3.8+")
        return False

def check_dependencies():
    """Check required dependencies"""
    print_section("Dependencies Check")
    
    required_packages = ['flask', 'yt-dlp', 'waitress']
    all_good = True
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"✅ {package} is installed")
        except ImportError:
            print(f"❌ {package} is NOT installed")
            all_good = False
    
    # Check yt-dlp version
    try:
        version = yt_dlp.version.__version__
        print(f"📦 yt-dlp version: {version}")
        
        # Check if version is recent (2025.x.x)
        if version.startswith('2025'):
            print("✅ yt-dlp version is recent")
        else:
            print("⚠️ yt-dlp version may be outdated")
    except:
        print("❌ Could not determine yt-dlp version")
        all_good = False
    
    return all_good

def check_ffmpeg():
    """Check ffmpeg installation"""
    print_section("FFmpeg Check")
    
    # Check environment variables
    ffmpeg_env = os.environ.get('FFMPEG_LOCATION') or os.environ.get('FFMPEG_PATH')
    if ffmpeg_env:
        print(f"🔧 FFMPEG_LOCATION/FFMPEG_PATH set to: {ffmpeg_env}")
    else:
        print("⚠️ FFMPEG_LOCATION/FFMPEG_PATH not set")
    
    # Try to find ffmpeg
    ffmpeg_paths = [
        ffmpeg_env,
        'ffmpeg',
        'C:\\ffmpeg\\bin\\ffmpeg.exe',
        'C:\\Program Files\\ffmpeg\\bin\\ffmpeg.exe',
    ]
    
    for path in ffmpeg_paths:
        if not path:
            continue
        
        success, stdout, stderr = run_command(f'"{path}" -version')
        if success:
            version_line = stdout.split('\n')[0] if stdout else "Unknown version"
            print(f"✅ ffmpeg found at: {path}")
            print(f"   Version: {version_line}")
            return True
    
    print("❌ ffmpeg not found")
    print("💡 Install ffmpeg from https://ffmpeg.org/download.html")
    print("💡 Set FFMPEG_LOCATION environment variable to ffmpeg path")
    return False

def test_network_connectivity():
    """Test network connectivity to YouTube"""
    print_section("Network Connectivity Test")
    
    test_urls = [
        "https://www.youtube.com",
        "https://youtubei.googleapis.com",
        "https://www.googleapis.com"
    ]
    
    all_good = True
    for url in test_urls:
        try:
            import urllib.request
            urllib.request.urlopen(url, timeout=10)
            print(f"✅ Can reach {url}")
        except Exception as e:
            print(f"❌ Cannot reach {url}: {e}")
            all_good = False
    
    return all_good

def test_youtube_extraction():
    """Test YouTube video extraction with different clients"""
    print_section("YouTube Extraction Test")
    
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # Rick Roll - should always work
    clients = ['android_creator', 'android_music', 'android', 'web', 'ios']
    
    working_clients = []
    
    for client in clients:
        try:
            print(f"Testing client: {client}...")
            
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'skip_download': True,
                'socket_timeout': 15,
                'extractor_args': {
                    'youtube': {
                        'player_client': client,
                        'skip': ['hls', 'dash'] if client.startswith('android') else ['hls']
                    }
                }
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(test_url, download=False)
            
            formats_count = len(info.get('formats', []))
            print(f"  ✅ {client}: {formats_count} formats available")
            working_clients.append(client)
            
        except Exception as e:
            print(f"  ❌ {client}: {str(e)[:100]}...")
    
    if working_clients:
        print(f"\n✅ Working clients: {', '.join(working_clients)}")
        return True
    else:
        print("\n❌ No clients are working")
        return False

def test_download():
    """Test actual download"""
    print_section("Download Test")
    
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    
    try:
        print("Testing download with safe format...")
        
        ydl_opts = {
            'quiet': False,
            'no_warnings': False,
            'format': '18',  # 360p MP4 - most compatible
            'outtmpl': 'downloads/test_%(id)s.%(ext)s',
            'socket_timeout': 30,
            'retries': 3,
            'extractor_args': {
                'youtube': {
                    'player_client': 'android',
                    'skip': ['hls', 'dash']
                }
            }
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([test_url])
        
        # Check if file was created
        test_files = [f for f in os.listdir('downloads') if 'dQw4w9WgXcQ' in f and f.startswith('test_')]
        if test_files:
            test_file = os.path.join('downloads', test_files[0])
            file_size = os.path.getsize(test_file)
            print(f"✅ Download successful: {test_files[0]} ({file_size:,} bytes)")
            
            # Clean up test file
            try:
                os.remove(test_file)
                print("🧹 Test file cleaned up")
            except:
                pass
            
            return True
        else:
            print("❌ Download completed but file not found")
            return False
            
    except Exception as e:
        print(f"❌ Download failed: {str(e)}")
        return False

def check_cookies():
    """Check cookies file"""
    print_section("Cookies Check")
    
    cookies_file = os.environ.get('COOKIES_FILE', 'cookies.txt')
    
    if os.path.exists(cookies_file):
        file_size = os.path.getsize(cookies_file)
        mod_time = datetime.fromtimestamp(os.path.getmtime(cookies_file))
        print(f"✅ Cookies file found: {cookies_file}")
        print(f"   Size: {file_size:,} bytes")
        print(f"   Modified: {mod_time}")
        
        # Check if cookies are recent (within 30 days)
        days_old = (datetime.now() - mod_time).days
        if days_old > 30:
            print(f"⚠️ Cookies are {days_old} days old - consider updating")
        else:
            print(f"✅ Cookies are recent ({days_old} days old)")
        
        return True
    else:
        print(f"⚠️ Cookies file not found: {cookies_file}")
        print("💡 Export cookies from your browser if you encounter 403 errors")
        return False

def check_disk_space():
    """Check available disk space"""
    print_section("Disk Space Check")
    
    try:
        import shutil
        total, used, free = shutil.disk_usage('.')
        
        print(f"💾 Disk space:")
        print(f"   Total: {total // (1024**3):,} GB")
        print(f"   Used:  {used // (1024**3):,} GB")
        print(f"   Free:  {free // (1024**3):,} GB")
        
        if free < 1024**3:  # Less than 1GB
            print("⚠️ Low disk space - may cause download failures")
            return False
        else:
            print("✅ Sufficient disk space available")
            return True
            
    except Exception as e:
        print(f"❌ Could not check disk space: {e}")
        return False

def generate_report():
    """Generate a comprehensive diagnostic report"""
    print_header("YOUTUBE DOWNLOADER DIAGNOSTIC REPORT")
    
    results = {}
    
    # Run all checks
    results['python'] = check_python_version()
    results['dependencies'] = check_dependencies()
    results['ffmpeg'] = check_ffmpeg()
    results['network'] = test_network_connectivity()
    results['extraction'] = test_youtube_extraction()
    results['cookies'] = check_cookies()
    results['disk_space'] = check_disk_space()
    results['download'] = test_download()
    
    # Summary
    print_header("DIAGNOSTIC SUMMARY")
    
    passed = sum(results.values())
    total = len(results)
    
    print(f"📊 Tests passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All tests passed! Your YouTube downloader should work perfectly.")
    elif passed >= total * 0.75:
        print("✅ Most tests passed. Minor issues detected but should work.")
    elif passed >= total * 0.5:
        print("⚠️ Some issues detected. YouTube downloading may be unreliable.")
    else:
        print("❌ Major issues detected. YouTube downloading likely won't work.")
    
    # Recommendations
    print_section("Recommendations")
    
    if not results['python']:
        print("🔧 Update Python to version 3.8 or higher")
    
    if not results['dependencies']:
        print("🔧 Install missing dependencies: pip install -r requirements.txt")
    
    if not results['ffmpeg']:
        print("🔧 Install ffmpeg and set FFMPEG_LOCATION environment variable")
    
    if not results['network']:
        print("🔧 Check your internet connection and firewall settings")
    
    if not results['extraction']:
        print("🔧 Update yt-dlp: pip install --upgrade yt-dlp")
        print("🔧 Check if YouTube is blocking your IP")
    
    if not results['cookies']:
        print("🔧 Export cookies from your browser if you encounter 403 errors")
    
    if not results['disk_space']:
        print("🔧 Free up disk space")
    
    if not results['download']:
        print("🔧 Check logs for specific error messages")
        print("🔧 Try using different format options")
    
    print_header("DIAGNOSTIC COMPLETE")

def main():
    """Main function"""
    print("🚀 YouTube Downloader Troubleshooting Script")
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Ensure downloads directory exists
    os.makedirs('downloads', exist_ok=True)
    
    # Generate full report
    generate_report()

if __name__ == "__main__":
    main()