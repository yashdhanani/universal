import os
from typing import Dict, Any, Optional
import yt_dlp

from .celery_app import celery
from .progress import set_progress
from ..platforms.youtube import prepare_download  # reuse existing logic


def _find_final_file(outdir: str, video_id: Optional[str]) -> str:
    """Find the newest file for the video id in outdir."""
    chosen = None
    newest = -1
    for f in os.listdir(outdir):
        if (not video_id) or (video_id in f):
            p = os.path.join(outdir, f)
            if os.path.isfile(p):
                m = os.path.getmtime(p)
                if m > newest:
                    newest = m
                    chosen = p
    if not chosen:
        raise RuntimeError("File not found after download/merge")
    return chosen


@celery.task(bind=True, name="download.youtube")
def download_task(self, url: str, format_id: str) -> Dict[str, Any]:
    task_id = self.request.id
    ydl_opts, outdir = prepare_download(url, format_id)

    def hook(d):
        st = d.get("status")
        if st == "downloading":
            p_str = (d.get("_percent_str") or "").strip().replace("%", "")
            try:
                percent = float(p_str) if p_str else None
            except Exception:
                percent = None
            set_progress(task_id, "downloading", percent=percent, eta=d.get("eta"))
        elif st in ("finished", "complete"):
            set_progress(task_id, "processing", detail="Merging")

    ydl_opts["progress_hooks"] = [hook]

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)

    video_id = (info or {}).get("id")
    final_path = _find_final_file(outdir, video_id)

    set_progress(task_id, "finished", percent=100.0, eta=0)
    return {
        "path": final_path,
        "id": video_id,
        "title": (info or {}).get("title"),
        "ext": os.path.splitext(final_path)[1].lstrip("."),
        "filesize": os.path.getsize(final_path),
    }