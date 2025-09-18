import os
import shutil
import json
import time
from typing import Dict, Any, Optional


def _safe_bool(val: Optional[str], default: bool = False) -> bool:
    try:
        if isinstance(val, bool):
            return val
        s = str(val or "").strip().lower()
        if s in ("1", "true", "yes", "on"):  # noqa: PLC1901
            return True
        if s in ("0", "false", "no", "off"):
            return False
        return default
    except Exception:
        return default


def _fmt(template: str, data: Dict[str, Any]) -> str:
    # Safe simple formatter with {key} placeholders only
    try:
        class _D(dict):
            def __missing__(self, k):
                return ""
        return template.format_map(_D(data))
    except Exception:
        return template


def _download_thumbnail(thumbnail_url: Optional[str], dest_dir: str, base_name: str) -> Optional[str]:
    if not thumbnail_url:
        return None
    try:
        import requests  # type: ignore
        os.makedirs(dest_dir, exist_ok=True)
        headers = {
            'User-Agent': os.environ.get('USER_AGENT', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'),
            'Accept': '*/*',
            'Accept-Language': os.environ.get('ACCEPT_LANGUAGE', 'en-US,en;q=0.9')
        }
        r = requests.get(thumbnail_url, headers=headers, timeout=15)
        r.raise_for_status()
        # Guess extension
        ext = 'jpg'
        ct = r.headers.get('Content-Type', '')
        if 'png' in ct:
            ext = 'png'
        elif 'webp' in ct:
            ext = 'webp'
        out = os.path.join(dest_dir, f"{base_name}.{ext}")
        with open(out, 'wb') as f:
            f.write(r.content)
        return out
    except Exception:
        return None


def run_post_download(meta: Dict[str, Any], success: bool = True, error: Optional[str] = None) -> Dict[str, Any]:
    """
    Post-download actions controlled by environment variables.
    Supported env vars:
    - POSTDL_MOVE_TEMPLATE: destination path template, e.g. e:\\Media\\{platform}\\{uploader}\\{title} [{id}].{ext}
    - POSTDL_WEBHOOK_URL: HTTP endpoint to POST JSON payload
    - POSTDL_COMMAND: Command template to execute (placeholders allowed)
    - POSTDL_OPEN_AFTER: 1/0 open file after processing
    - POSTDL_THUMBNAIL: 1/0 download thumbnail alongside file
    - POSTDL_ENABLED: 1/0 master toggle (defaults to enabled if any action set)
    """
    actions = {
        'move_template': os.environ.get('POSTDL_MOVE_TEMPLATE', '').strip(),
        'webhook_url': os.environ.get('POSTDL_WEBHOOK_URL', '').strip(),
        'command': os.environ.get('POSTDL_COMMAND', '').strip(),
        'open_after': _safe_bool(os.environ.get('POSTDL_OPEN_AFTER'), False),
        'thumbnail': _safe_bool(os.environ.get('POSTDL_THUMBNAIL'), False),
    }
    enabled_env = os.environ.get('POSTDL_ENABLED')
    enabled = _safe_bool(enabled_env, any(actions.values()))
    result: Dict[str, Any] = {'enabled': enabled, 'actions': [], 'errors': []}

    if not enabled:
        return result

    path = meta.get('path') or ''
    filename = meta.get('filename') or (os.path.basename(path) if path else '')
    ext = meta.get('ext') or (os.path.splitext(filename)[1].lstrip('.') if filename else '')

    # 1) Move/Rename
    if actions['move_template'] and path and os.path.isfile(path):
        try:
            dst = _fmt(actions['move_template'], {
                **meta,
                'filename': filename,
                'ext': ext,
            })
            dst_dir = os.path.dirname(dst)
            os.makedirs(dst_dir, exist_ok=True)
            # Ensure extension in template
            if not os.path.splitext(dst)[1] and ext:
                dst = dst + f'.{ext}'
            shutil.move(path, dst)
            meta['path'] = dst
            meta['filename'] = os.path.basename(dst)
            result['actions'].append({'move_to': dst})
            path = dst
        except Exception as e:
            result['errors'].append(f"move_failed: {e}")

    # Base directory for thumbnails and command working dir
    work_dir = os.path.dirname(path) if path else os.getcwd()

    # 2) Thumbnail save
    thumb_saved = None
    if actions['thumbnail']:
        try:
            base_name, _ = os.path.splitext(meta.get('filename') or 'thumbnail')
            thumb_saved = _download_thumbnail(meta.get('thumbnail') or meta.get('thumbnail_url'), work_dir, base_name)
            if thumb_saved:
                result['actions'].append({'thumbnail_saved': thumb_saved})
        except Exception as e:
            result['errors'].append(f"thumbnail_failed: {e}")

    # 3) Webhook
    if actions['webhook_url']:
        try:
            import requests  # type: ignore
            payload = {
                'timestamp': int(time.time()),
                'success': success,
                'error': error,
                'meta': meta,
                'thumbnail_saved': thumb_saved,
            }
            headers = {'Content-Type': 'application/json'}
            r = requests.post(actions['webhook_url'], data=json.dumps(payload, ensure_ascii=False).encode('utf-8'), headers=headers, timeout=10)
            result['actions'].append({'webhook_status': r.status_code})
        except Exception as e:
            result['errors'].append(f"webhook_failed: {e}")

    # 4) External command
    if actions['command']:
        try:
            import subprocess
            cmd = _fmt(actions['command'], meta)
            # Run via shell to allow templates/path quoting by user
            completed = subprocess.run(cmd, shell=True, cwd=work_dir, capture_output=True, text=True)
            result['actions'].append({'command': cmd, 'returncode': completed.returncode})
            if completed.returncode != 0:
                result['errors'].append(f"command_failed: {completed.stderr.strip()}")
        except Exception as e:
            result['errors'].append(f"command_error: {e}")

    # 5) Open after
    if actions['open_after'] and path and os.path.isfile(path):
        try:
            os.startfile(path)  # type: ignore[attr-defined]
            result['actions'].append({'opened': True})
        except Exception as e:
            result['errors'].append(f"open_failed: {e}")

    return result