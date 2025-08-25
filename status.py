#!/usr/bin/env python3
"""
YouTube Downloader Status Check
Shows current system status and available options
"""

import os
import sys
import yt_dlp
from datetime import datetime

def print_banner():
    """Print status banner"""
    print("🎯 YouTube Downloader - System Status")
    print("=" * 50)
    print(f"⏰ Status check: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

def check_system_status():
    """Check overall system status"""
    print("📊 System Status:")
    print("-" * 20)
    
    # Python version
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    print(f"🐍 Python: {python_version} {'✅' if sys.version_info >= (3, 8) else '❌'}")
    
    # yt-dlp version
    try:
        ytdlp_version = yt_dlp.version.__version__
        is_recent = ytdlp_version.startswith('2025')
        print(f"📦 yt-dlp: {ytdlp_version} {'✅' if is_recent else '⚠️'}")
    except:
        print("📦 yt-dlp: Unknown ❌")
    
    # Dependencies
    deps = ['flask', 'waitress']
    all_deps_ok = True
    for dep in deps:
        try:
            __import__(dep)
            print(f"📚 {dep}: Installed ✅")
        except ImportError:
            print(f"📚 {dep}: Missing ❌")
            all_deps_ok = False
    
    # FFmpeg
    ffmpeg_available = False
    ffmpeg_paths = [
        os.environ.get('FFMPEG_LOCATION'),
        os.environ.get('FFMPEG_PATH'),
        'ffmpeg'
    ]
    
    for path in ffmpeg_paths:
        if path:
            try:
                import subprocess
                result = subprocess.run([path, '-version'], capture_output=True, timeout=5)
                if result.returncode == 0:
                    print(f"🎬 FFmpeg: Available ✅")
                    ffmpeg_available = True
                    break
            except:
                continue
    
    if not ffmpeg_available:
        print("🎬 FFmpeg: Not found ⚠️")
    
    # Cookies
    cookies_file = os.environ.get('COOKIES_FILE', 'cookies.txt')
    if os.path.exists(cookies_file):
        file_size = os.path.getsize(cookies_file)
        print(f"🍪 Cookies: Available ({file_size} bytes) ✅")
    else:
        print("🍪 Cookies: Not found ⚠️")
    
    print()
    return all_deps_ok and ffmpeg_available

def show_available_scripts():
    """Show available scripts and their purposes"""
    print("🚀 Available Scripts:")
    print("-" * 20)
    
    scripts = [
        ("start_fixed.py", "🎯 Enhanced startup with auto-fixes", "Recommended for daily use"),
        ("start_development.bat", "🔧 Windows development startup", "Easy Windows startup"),
        ("app.py", "⚙️ Direct Flask app startup", "Basic startup (no auto-fixes)"),
        ("quick_test.py", "🧪 Fast functionality test", "Quick verification"),
        ("troubleshoot.py", "🔍 Full system diagnostics", "When things go wrong"),
        ("update_ytdlp.py", "📦 Update yt-dlp only", "Keep yt-dlp current"),
        ("status.py", "📊 This status script", "Check system status"),
    ]
    
    for script, description, purpose in scripts:
        if os.path.exists(script):
            print(f"✅ {script:<20} {description}")
            print(f"   └─ {purpose}")
        else:
            print(f"❌ {script:<20} Missing")
    
    print()

def show_usage_examples():
    """Show usage examples"""
    print("💡 Usage Examples:")
    print("-" * 20)
    
    examples = [
        ("Start the app (recommended)", "python start_fixed.py"),
        ("Start on Windows", "start_development.bat"),
        ("Quick test", "python quick_test.py"),
        ("Full diagnostics", "python troubleshoot.py"),
        ("Update yt-dlp", "python update_ytdlp.py"),
        ("Check status", "python status.py"),
    ]
    
    for description, command in examples:
        print(f"🔹 {description}:")
        print(f"   {command}")
    
    print()

def show_web_interface_info():
    """Show web interface information"""
    print("🌐 Web Interface:")
    print("-" * 20)
    print("📱 Main interface: http://127.0.0.1:5000")
    print("🔄 Universal interface: http://127.0.0.1:5000/universal")
    print("🧹 Clear downloads: http://127.0.0.1:5000/clear_downloads")
    print()
    
    print("📋 API Endpoints:")
    print("   POST /api/video_info - Get video information")
    print("   POST /api/download - Start download")
    print("   GET  /api/progress/<task_id> - Check progress")
    print("   GET  /download/<filename> - Download file")
    print()

def show_troubleshooting_tips():
    """Show quick troubleshooting tips"""
    print("🔧 Quick Troubleshooting:")
    print("-" * 20)
    
    tips = [
        ("403 Forbidden errors", "Update cookies.txt from browser"),
        ("Format not available", "Try 'Best' format or different quality"),
        ("Slow downloads", "Install aria2c external downloader"),
        ("Video won't merge", "Check FFmpeg installation"),
        ("App won't start", "Run 'python troubleshoot.py'"),
        ("Old yt-dlp version", "Run 'python update_ytdlp.py'"),
    ]
    
    for problem, solution in tips:
        print(f"❓ {problem}:")
        print(f"   💡 {solution}")
    
    print()

def main():
    """Main status function"""
    print_banner()
    
    # Check system status
    system_ok = check_system_status()
    
    # Show available scripts
    show_available_scripts()
    
    # Show usage examples
    show_usage_examples()
    
    # Show web interface info
    show_web_interface_info()
    
    # Show troubleshooting tips
    show_troubleshooting_tips()
    
    # Final recommendation
    print("🎯 Recommendation:")
    print("-" * 20)
    if system_ok:
        print("✅ System looks good! Run 'python start_fixed.py' to start.")
    else:
        print("⚠️ Some issues detected. Run 'python troubleshoot.py' first.")
    
    print()
    print("🎉 YouTube Downloader is ready for 2025!")
    print("=" * 50)

if __name__ == "__main__":
    main()