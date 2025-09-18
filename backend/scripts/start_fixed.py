#!/usr/bin/env python3
"""
Enhanced startup script for YouTube Downloader
Automatically fixes common issues and starts the application
"""

import os
import sys
import subprocess
import threading
import time
import argparse
from datetime import datetime

def print_banner():
    """Print startup banner"""
    print("🚀 YouTube Downloader - Enhanced Startup")
    print("=" * 50)
    print(f"⏰ Starting at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("🔧 Checking and fixing common issues...")
    print()

def run_command(cmd, timeout=30):
    """Run a command with timeout"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out"
    except Exception as e:
        return False, "", str(e)

def check_and_install_dependencies():
    """Check and install missing dependencies"""
    print("📦 Checking dependencies...")
    
    required_packages = ['flask', 'yt-dlp', 'waitress']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"  ✅ {package}")
        except ImportError:
            print(f"  ❌ {package} - MISSING")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n🔧 Installing missing packages: {', '.join(missing_packages)}")
        for package in missing_packages:
            success, stdout, stderr = run_command(f"python -m pip install {package}")
            if success:
                print(f"  ✅ Installed {package}")
            else:
                print(f"  ❌ Failed to install {package}: {stderr}")
                return False
    
    return True

def update_ytdlp():
    """Update yt-dlp to latest version"""
    print("\n🔄 Updating yt-dlp...")
    
    success, stdout, stderr = run_command("python -m pip install --upgrade yt-dlp")
    if success:
        print("  ✅ yt-dlp updated successfully")
        return True
    else:
        print(f"  ⚠️ Update failed: {stderr}")
        # Try to continue anyway
        return True

def setup_environment():
    """Setup environment variables and directories"""
    print("\n🏗️ Setting up environment...")
    
    # Create necessary directories
    directories = ['downloads', 'logs']
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"  ✅ Created directory: {directory}")
        else:
            print(f"  ✅ Directory exists: {directory}")
    
    # Set default environment variables if not set
    env_vars = {
        'FLASK_ENV': 'development',
        'PYTHONUNBUFFERED': '1',
    }
    
    for var, value in env_vars.items():
        if not os.environ.get(var):
            os.environ[var] = value
            print(f"  ✅ Set {var}={value}")
    
    # Check for ffmpeg
    ffmpeg_paths = [
        os.environ.get('FFMPEG_LOCATION'),
        os.environ.get('FFMPEG_PATH'),
        'C:\\ffmpeg\\bin\\ffmpeg.exe',
        'ffmpeg'
    ]
    
    ffmpeg_found = False
    for path in ffmpeg_paths:
        if not path:
            continue
        
        success, _, _ = run_command(f'"{path}" -version')
        if success:
            if not os.environ.get('FFMPEG_LOCATION'):
                os.environ['FFMPEG_LOCATION'] = path
            print(f"  ✅ ffmpeg found: {path}")
            ffmpeg_found = True
            break
    
    if not ffmpeg_found:
        print("  ⚠️ ffmpeg not found - video merging may not work")
        print("     Install from: https://ffmpeg.org/download.html")
    
    return True

def test_basic_functionality(test_url: str | None = None):
    """Test basic YouTube functionality (fast, extraction-only).
    Uses a short official yt-dlp test clip by default.
    """
    print("\n🧪 Testing basic functionality...")
    
    try:
        import yt_dlp
        
        # Prefer a tiny test clip to minimize network time
        test_url = test_url or "https://www.youtube.com/watch?v=BaW_jenozKc"  # yt-dlp test video (~9s)
        
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,  # extraction only
            'socket_timeout': 10,
            'retries': 1,
            'extractor_args': {
                'youtube': {
                    'player_client': 'android',  # single client for speed
                }
            }
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(test_url, download=False)
        
        print(f"  ✅ YouTube extraction working")
        print(f"     Test video: {info.get('title', 'Unknown')}")
        print(f"     Formats available: {len(info.get('formats', []))}")
        return True
        
    except Exception as e:
        print(f"  ⚠️ Basic test failed: {str(e)[:100]}...")
        print("     App may still work, continuing...")
        return True  # Continue anyway

def cleanup_old_files():
    """Clean up old temporary files"""
    print("\n🧹 Cleaning up old files...")
    
    try:
        # Clean up old downloads (optional)
        downloads_dir = 'downloads'
        if os.path.exists(downloads_dir):
            files = os.listdir(downloads_dir)
            old_files = [f for f in files if f.endswith('.part') or f.endswith('.tmp')]
            
            for file in old_files:
                try:
                    os.remove(os.path.join(downloads_dir, file))
                    print(f"  🗑️ Removed: {file}")
                except:
                    pass
            
            if not old_files:
                print("  ✅ No temporary files to clean")
        
        # Clean up old logs (keep last 5)
        logs_dir = 'logs'
        if os.path.exists(logs_dir):
            log_files = [f for f in os.listdir(logs_dir) if f.startswith('app.log.')]
            log_files.sort()
            
            if len(log_files) > 5:
                for old_log in log_files[:-5]:
                    try:
                        os.remove(os.path.join(logs_dir, old_log))
                        print(f"  🗑️ Removed old log: {old_log}")
                    except:
                        pass
        
        return True
        
    except Exception as e:
        print(f"  ⚠️ Cleanup failed: {e}")
        return True  # Continue anyway

def start_application():
    """Start the Flask application"""
    print("\n🚀 Starting YouTube Downloader application...")
    print("=" * 50)
    print("🌐 Server will be available at: http://127.0.0.1:5000")
    print("📱 Mobile-friendly interface included")
    print("🔄 Auto-restart on file changes (development mode)")
    print("=" * 50)
    print()
    
    try:
        # Import and run the app
        from app import app, cleanup_old_tasks
        
        # Start the cleanup thread
        cleanup_thread = threading.Thread(target=cleanup_old_tasks, daemon=True)
        cleanup_thread.start()
        
        # Configure app for development
        app.config['TEMPLATES_AUTO_RELOAD'] = True
        
        # Start the Flask app
        app.run(
            debug=True,
            threaded=True,
            host='127.0.0.1',
            port=5000,
            use_reloader=True
        )
        
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down gracefully...")
        print("Thank you for using YouTube Downloader!")
    except Exception as e:
        print(f"\n❌ Failed to start application: {e}")
        print("\n🔧 Troubleshooting steps:")
        print("1. Run: python troubleshoot.py")
        print("2. Check logs/app.log for errors")
        print("3. Ensure all dependencies are installed")
        return False
    
    return True

def main():
    """Main startup function with fast dev options"""
    print_banner()

    # Parse CLI and env flags
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--fast", action="store_true", help="Skip yt-dlp update and tests for faster startup")
    parser.add_argument("--skip-update", action="store_true", help="Skip yt-dlp update step")
    parser.add_argument("--skip-tests", action="store_true", help="Skip functionality tests")
    parser.add_argument("--skip-deps", action="store_true", help="Skip dependency checks/installs")
    args, _ = parser.parse_known_args()

    # Enable fast mode automatically in development
    fast = (
        args.fast
        or os.environ.get("FAST_DEV", "0") == "1"
        or os.environ.get("FLASK_ENV", "").lower() == "development"
    )

    skip_update = fast or args.skip_update or os.environ.get("SKIP_UPDATE", "0") == "1"
    skip_tests = fast or args.skip_tests or os.environ.get("SKIP_TESTS", "0") == "1"
    skip_deps = args.skip_deps or os.environ.get("SKIP_DEPS", "0") == "1"

    if fast:
        print("⚡ Fast dev mode enabled: skipping yt-dlp update and tests. Use --skip-deps to also skip dependency check.")

    # Build steps conditionally
    steps = []
    if not skip_deps:
        steps.append(("Installing dependencies", check_and_install_dependencies))
    if not skip_update:
        steps.append(("Updating yt-dlp", update_ytdlp))
    steps.append(("Setting up environment", setup_environment))
    if not skip_tests:
        # Allow overriding test URL via env or CLI
        test_url = os.environ.get("DEV_TEST_URL")
        steps.append(("Testing functionality", lambda: test_basic_functionality(test_url)))
    steps.append(("Cleaning up files", cleanup_old_files))

    for step_name, step_func in steps:
        print(f"🔄 {step_name}...")
        if not step_func():
            print(f"❌ {step_name} failed!")
            print("🔧 Run 'python troubleshoot.py' for detailed diagnostics")
            return False
        print(f"✅ {step_name} completed")

    print("\n🎉 Setup steps completed!")
    print("🚀 Starting application...")

    # Start the application
    return start_application()

if __name__ == "__main__":
    try:
        success = main()
        if not success:
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n👋 Startup cancelled by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n💥 Unexpected error during startup: {e}")
        print("🔧 Run 'python troubleshoot.py' for help")
        sys.exit(1)