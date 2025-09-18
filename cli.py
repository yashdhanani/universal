import argparse
import os
import sys
from urllib.parse import urlparse
from backend.platforms.base import analyze_platform, prepare_download_options
import importlib
import json
import yt_dlp

def get_platform_from_url(url):
    hostname = urlparse(url).hostname
    if not hostname:
        return None
    
    if 'youtube.com' in hostname or 'youtu.be' in hostname:
        return 'youtube'
    if 'instagram.com' in hostname:
        return 'instagram'
    if 'facebook.com' in hostname:
        return 'facebook'
    if 'tiktok.com' in hostname:
        return 'tiktok'
    if 'twitter.com' in hostname or 'x.com' in hostname:
        return 'twitter'
    if 'pinterest.com' in hostname:
        return 'pinterest'
    if 'reddit.com' in hostname:
        return 'reddit'
    if 'snapchat.com' in hostname:
        return 'snapchat'
    if 'linkedin.com' in hostname:
        return 'linkedin'
    return None

def analyze(args):
    platform = get_platform_from_url(args.url)
    if not platform:
        print(f"Error: Could not determine platform for URL: {args.url}", file=sys.stderr)
        sys.exit(1)

    try:
        platform_module = importlib.import_module(f"backend.platforms.{platform}")
        result = platform_module.analyze(args.url)
        print(json.dumps(result, indent=2))

    except ImportError:
        print(f"Error: Platform '{platform}' not supported", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"An error occurred: {e}", file=sys.stderr)
        sys.exit(1)

def download(args):
    platform = get_platform_from_url(args.url)
    if not platform:
        print(f"Error: Could not determine platform for URL: {args.url}", file=sys.stderr)
        sys.exit(1)

    try:
        platform_module = importlib.import_module(f"backend.platforms.{platform}")
        ydl_opts, _ = platform_module.prepare_download(args.url, args.format_id)

        if ydl_opts.get('direct_url'):
            print(f"Downloading directly from: {ydl_opts['direct_url']}")
            # Here you would use requests or another library to download the file
            # For simplicity, we'll just print the URL
        else:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(args.url, download=True)
            # Determine final file path (newest by id in outdir)
            from backend.utils.post_download import run_post_download
            import glob, time
            video_id = None
            if info:
                if info.get('_type') == 'playlist':
                    entries = info.get('entries') or []
                    if entries:
                        info = entries[0]
                video_id = info.get('id')
            outtmpl = ydl_opts.get('outtmpl') or ''
            outdir = os.path.dirname(outtmpl) if outtmpl else os.path.join(os.getcwd(), 'downloads')
            final_path = None
            try:
                candidates = []
                for f in os.listdir(outdir):
                    if (not video_id) or (video_id in f):
                        p = os.path.join(outdir, f)
                        if os.path.isfile(p):
                            candidates.append((os.path.getmtime(p), p))
                if candidates:
                    candidates.sort(reverse=True)
                    final_path = candidates[0][1]
            except Exception:
                pass
            if final_path:
                meta = {
                    'success': True,
                    'path': final_path,
                    'filename': os.path.basename(final_path),
                    'id': video_id,
                    'title': info.get('title') if isinstance(info, dict) else None,
                    'uploader': info.get('uploader') if isinstance(info, dict) else None,
                    'platform': get_platform_from_url(args.url) or 'unknown',
                    'ext': os.path.splitext(final_path)[1].lstrip('.'),
                    'filesize': os.path.getsize(final_path) if os.path.exists(final_path) else None,
                    'url': args.url,
                    'format_id': args.format_id,
                    'thumbnail': (info.get('thumbnail') if isinstance(info, dict) else None),
                }
                try:
                    run_post_download(meta, success=True)
                except Exception:
                    pass
        print("Download complete.")

    except ImportError:
        print(f"Error: Platform '{platform}' not supported", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"An error occurred during download: {e}", file=sys.stderr)
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description='Downloader CLI')
    subparsers = parser.add_subparsers(dest='command', required=True)

    # Analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze a URL and get media info')
    analyze_parser.add_argument('url', help='URL to analyze')
    analyze_parser.set_defaults(func=analyze)

    # Download command
    download_parser = subparsers.add_parser('download', help='Download media from a URL')
    download_parser.add_argument('url', help='URL to download')
    download_parser.add_argument('-f', '--format', dest='format_id', default='best', help='Format ID to download')
    download_parser.set_defaults(func=download)

    # Global arguments
    for sub_parser in [analyze_parser, download_parser]:
        sub_parser.add_argument('--cookies', help='Path to cookies file')
        sub_parser.add_argument('--browser', help='Browser to load cookies from')
        sub_parser.add_argument('--proxy', help='Proxy to use')

    args = parser.parse_args()

    if args.cookies:
        os.environ['COOKIES_FILE'] = args.cookies
    
    if args.browser:
        os.environ['YTDLP_COOKIES_FROM_BROWSER'] = args.browser

    args.func(args)

if __name__ == '__main__':
    main()
