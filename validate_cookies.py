#!/usr/bin/env python3
"""
Cookie Validation Utility
Validates cookies.txt format and tests with yt-dlp
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path

def validate_netscape_format(cookies_file):
    """Validate if cookies file is in Netscape format"""
    try:
        with open(cookies_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        lines = content.strip().split('\n')
        if not lines:
            return False, "Empty file"

        # Check for Netscape header
        has_header = any('# Netscape HTTP Cookie File' in line for line in lines[:5])

        # Check for tab-separated format
        tab_lines = [line for line in lines if line.strip() and not line.startswith('#')]
        has_tabs = any('\t' in line for line in tab_lines[:3])

        # Check for JSON format (invalid)
        is_json = content.strip().startswith('{')

        if is_json:
            return False, "JSON format detected - use Netscape format instead"

        if not has_tabs and not has_header:
            return False, "Not in Netscape format (missing tabs and header)"

        if has_header or has_tabs:
            return True, "Valid Netscape format"

        return False, "Unrecognized format"

    except Exception as e:
        return False, f"Error reading file: {e}"

def test_with_yt_dlp(cookies_file, test_url="https://www.youtube.com/watch?v=jNQXAC9IVRw"):
    """Test cookies with yt-dlp"""
    try:
        # First validate format
        valid, message = validate_netscape_format(cookies_file)
        if not valid:
            print(f"❌ Cookie validation failed: {message}")
            return False

        print(f"✅ Cookie format validation passed: {message}")

        # Test with yt-dlp
        cmd = [
            sys.executable, "-m", "yt_dlp",
            "--cookies", cookies_file,
            "--dump-json",
            "--no-download",
            "--quiet",
            test_url
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            print("✅ yt-dlp cookie test PASSED - cookies are working!")
            return True
        else:
            print(f"❌ yt-dlp cookie test FAILED (exit code {result.returncode})")
            if result.stderr:
                print(f"Error: {result.stderr.strip()[:200]}")
            return False

    except subprocess.TimeoutExpired:
        print("❌ yt-dlp test timed out")
        return False
    except Exception as e:
        print(f"❌ yt-dlp test error: {e}")
        return False

def find_cookies_files():
    """Find all cookies files in the project"""
    cookies_dir = Path("cookies")
    files = []

    # Check main cookies.txt
    if Path("cookies.txt").exists():
        files.append(("cookies.txt", "main"))

    # Check platform-specific cookies
    if cookies_dir.exists():
        for platform_dir in cookies_dir.iterdir():
            if platform_dir.is_dir():
                for cookie_file in platform_dir.glob("*.txt"):
                    files.append((str(cookie_file), platform_dir.name))

    return files

def main():
    parser = argparse.ArgumentParser(description="Validate cookies.txt format and test with yt-dlp")
    parser.add_argument("cookies_file", nargs="?", help="Path to cookies file (optional - will scan if not provided)")
    parser.add_argument("--test-url", default="https://www.youtube.com/watch?v=jNQXAC9IVRw",
                       help="URL to test cookies with")
    parser.add_argument("--list", action="store_true", help="List all found cookie files")

    args = parser.parse_args()

    if args.list:
        print("Found cookie files:")
        files = find_cookies_files()
        if not files:
            print("  No cookie files found")
        else:
            for path, platform in files:
                print(f"  {path} ({platform})")
        return

    if args.cookies_file:
        cookies_files = [(args.cookies_file, "specified")]
    else:
        cookies_files = find_cookies_files()
        if not cookies_files:
            print("❌ No cookie files found in project")
            print("💡 Create cookies.txt or use browser extension to export cookies")
            return

    print(f"Testing {len(cookies_files)} cookie file(s)...\n")

    success_count = 0
    for cookies_file, platform in cookies_files:
        print(f"🔍 Testing: {cookies_file} ({platform})")
        if test_with_yt_dlp(cookies_file, args.test_url):
            success_count += 1
        print()

    if success_count == 0:
        print("❌ No working cookies found")
        print("\n💡 To fix:")
        print("1. Install browser extension: 'Get cookies.txt' or similar")
        print("2. Export cookies from youtube.com while logged in")
        print("3. Save as Netscape format to cookies.txt")
        print("4. Run: python validate_cookies.py cookies.txt")
    else:
        print(f"✅ {success_count} cookie file(s) working correctly")

if __name__ == "__main__":
    main()