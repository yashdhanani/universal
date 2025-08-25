#!/usr/bin/env python3
"""
YouTube Downloader - Live Demonstration
Shows the enhanced functionality working
"""

import os
import sys
import time
from datetime import datetime

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def print_banner():
    """Print demo banner"""
    print("🎬 YouTube Downloader - Live Demo")
    print("=" * 50)
    print(f"⏰ Demo started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

def demo_enhanced_ytdlp_config():
    """Demonstrate the enhanced yt-dlp configuration"""
    print("🔧 Demonstrating Enhanced yt-dlp Configuration")
    print("-" * 50)
    
    try:
        from app import build_ydl_opts
        
        # Build enhanced options
        opts = build_ydl_opts()
        
        print("✅ Enhanced yt-dlp options loaded:")
        print(f"   🌐 User-Agent: {opts['http_headers']['User-Agent'][:60]}...")
        print(f"   🔄 Retries: {opts['retries']}")
        print(f"   ⏱️ Socket Timeout: {opts['socket_timeout']}s")
        print(f"   🎯 YouTube Clients: {opts['extractor_args']['youtube']['player_client']}")
        print(f"   🚫 Skip Formats: {opts['extractor_args']['youtube']['skip']}")
        print(f"   🎬 FFmpeg: {'✅ Configured' if opts.get('ffmpeg_location') else '⚠️ Not set'}")
        print(f"   🍪 Cookies: {'✅ Available' if opts.get('cookiefile') else '⚠️ Not set'}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error loading configuration: {e}")
        return False

def demo_video_info_extraction():
    """Demonstrate video info extraction"""
    print("\n📺 Demonstrating Video Info Extraction")
    print("-" * 50)
    
    try:
        import yt_dlp
        from app import build_ydl_opts
        
        test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        print(f"🔍 Testing URL: {test_url}")
        
        # Test with enhanced configuration
        ydl_opts = build_ydl_opts({'skip_download': True})
        
        print("🔄 Extracting video information...")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(test_url, download=False)
        
        print("✅ Video information extracted successfully!")
        print(f"   📝 Title: {info.get('title', 'Unknown')}")
        print(f"   👤 Uploader: {info.get('uploader', 'Unknown')}")
        print(f"   ⏱️ Duration: {info.get('duration', 0)} seconds")
        print(f"   👁️ Views: {info.get('view_count', 0):,}")
        print(f"   📅 Upload Date: {info.get('upload_date', 'Unknown')}")
        print(f"   🎬 Formats Available: {len(info.get('formats', []))}")
        
        # Show format examples
        formats = info.get('formats', [])
        if formats:
            print("\n   📋 Sample Formats:")
            video_formats = [f for f in formats if f.get('vcodec') != 'none' and f.get('height')]
            audio_formats = [f for f in formats if f.get('acodec') != 'none' and f.get('vcodec') == 'none']
            
            print("      🎥 Video Formats:")
            for i, fmt in enumerate(video_formats[:3]):
                height = fmt.get('height', 'Unknown')
                ext = fmt.get('ext', 'Unknown')
                format_id = fmt.get('format_id', 'Unknown')
                fps = fmt.get('fps', 'Unknown')
                print(f"         {i+1}. {format_id}: {height}p @ {fps}fps ({ext})")
            
            print("      🎵 Audio Formats:")
            for i, fmt in enumerate(audio_formats[:2]):
                abr = fmt.get('abr', 'Unknown')
                ext = fmt.get('ext', 'Unknown')
                format_id = fmt.get('format_id', 'Unknown')
                print(f"         {i+1}. {format_id}: {abr}kbps ({ext})")
        
        return True
        
    except Exception as e:
        print(f"❌ Error extracting video info: {e}")
        return False

def demo_multiple_clients():
    """Demonstrate multiple client support"""
    print("\n🔄 Demonstrating Multiple Client Support")
    print("-" * 50)
    
    try:
        import yt_dlp
        from app import build_ydl_opts
        
        test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        clients = ['android_creator', 'android_music', 'android', 'web', 'ios']
        
        working_clients = []
        
        for client in clients:
            try:
                print(f"🧪 Testing client: {client}")
                
                ydl_opts = build_ydl_opts({'skip_download': True})
                ydl_opts['extractor_args']['youtube']['player_client'] = client
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(test_url, download=False)
                
                formats_count = len(info.get('formats', []))
                print(f"   ✅ {client}: {formats_count} formats available")
                working_clients.append((client, formats_count))
                
            except Exception as e:
                print(f"   ❌ {client}: {str(e)[:50]}...")
        
        print(f"\n📊 Results: {len(working_clients)}/{len(clients)} clients working")
        if working_clients:
            best_client = max(working_clients, key=lambda x: x[1])
            print(f"🏆 Best client: {best_client[0]} ({best_client[1]} formats)")
        
        return len(working_clients) > 0
        
    except Exception as e:
        print(f"❌ Error testing clients: {e}")
        return False

def demo_flask_app():
    """Demonstrate Flask app functionality"""
    print("\n🌐 Demonstrating Flask App")
    print("-" * 50)
    
    try:
        from app import app
        
        print("✅ Flask app imported successfully")
        print(f"   📱 App Name: {app.name}")
        print(f"   🔧 Debug Mode: {app.debug}")
        print(f"   🔑 Secret Key: {'✅ Set' if app.secret_key else '❌ Not set'}")
        
        # Show available routes
        print("\n   🛣️ Available Routes:")
        routes = []
        for rule in app.url_map.iter_rules():
            if rule.endpoint != 'static':
                methods = ', '.join(rule.methods - {'HEAD', 'OPTIONS'})
                routes.append((rule.rule, methods, rule.endpoint))
        
        for route, methods, endpoint in sorted(routes):
            print(f"      {methods:<12} {route}")
        
        print(f"\n   📊 Total Routes: {len(routes)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error loading Flask app: {e}")
        return False

def demo_file_structure():
    """Show the enhanced file structure"""
    print("\n📁 Enhanced File Structure")
    print("-" * 50)
    
    files = [
        ("app.py", "🎯 Main Flask application (enhanced)"),
        ("start_fixed.py", "🚀 Enhanced startup script"),
        ("troubleshoot.py", "🔍 Comprehensive diagnostics"),
        ("quick_test.py", "🧪 Fast functionality test"),
        ("update_ytdlp.py", "📦 yt-dlp updater"),
        ("status.py", "📊 System status checker"),
        ("test_server.py", "🌐 Server testing tool"),
        ("demo.py", "🎬 This demonstration script"),
        ("start_development.bat", "🪟 Windows startup script"),
        ("requirements.txt", "📋 Python dependencies"),
        ("cookies.txt", "🍪 YouTube cookies"),
        ("README_FIXES.md", "📖 Detailed fix documentation"),
        ("SOLUTION_SUMMARY.md", "📝 Complete solution summary"),
    ]
    
    print("✅ Enhanced YouTube Downloader Files:")
    for filename, description in files:
        if os.path.exists(filename):
            file_size = os.path.getsize(filename)
            print(f"   ✅ {filename:<20} {description} ({file_size:,} bytes)")
        else:
            print(f"   ❌ {filename:<20} {description} (missing)")
    
    # Show directories
    directories = ["downloads", "logs", "templates", "static"]
    print("\n📂 Directories:")
    for directory in directories:
        if os.path.exists(directory):
            file_count = len(os.listdir(directory))
            print(f"   ✅ {directory}/ ({file_count} files)")
        else:
            print(f"   ❌ {directory}/ (missing)")

def main():
    """Main demo function"""
    print_banner()
    
    # Run demonstrations
    demos = [
        ("Enhanced yt-dlp Configuration", demo_enhanced_ytdlp_config),
        ("Video Info Extraction", demo_video_info_extraction),
        ("Multiple Client Support", demo_multiple_clients),
        ("Flask App Functionality", demo_flask_app),
        ("File Structure", demo_file_structure),
    ]
    
    passed = 0
    total = len(demos)
    
    for demo_name, demo_func in demos:
        print(f"🔄 Running {demo_name} demo...")
        try:
            if demo_func():
                passed += 1
                print(f"✅ {demo_name} demo completed successfully")
            else:
                print(f"⚠️ {demo_name} demo completed with issues")
        except Exception as e:
            print(f"❌ {demo_name} demo failed: {e}")
        
        time.sleep(1)  # Brief pause between demos
    
    # Final summary
    print("\n" + "=" * 50)
    print("🎉 DEMONSTRATION COMPLETE")
    print("=" * 50)
    print(f"📊 Demos completed: {passed}/{total}")
    
    if passed == total:
        print("🏆 All demonstrations successful!")
        print("🚀 YouTube Downloader is fully operational with all enhancements!")
    elif passed >= total * 0.75:
        print("✅ Most demonstrations successful!")
        print("🎯 YouTube Downloader is working with minor issues.")
    else:
        print("⚠️ Some demonstrations had issues.")
        print("🔧 Run troubleshoot.py for detailed diagnostics.")
    
    print("\n🌐 To use the web interface:")
    print("   1. Run: python start_fixed.py")
    print("   2. Open: http://127.0.0.1:5000")
    print("   3. Enjoy seamless YouTube downloading!")
    
    print("\n🎯 The YouTube Downloader is ready for 2025! 🚀")
    print("=" * 50)

if __name__ == "__main__":
    main()