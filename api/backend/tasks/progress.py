import json
import os
import time
from typing import Optional, Dict, Any

try:
    import redis  # type: ignore
except Exception:
    redis = None

_redis = None
if redis:
    try:
        _redis = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"), decode_responses=True)
    except Exception:
        _redis = None

def set_progress(task_id: str, status: str, percent: Optional[float] = None, eta: Optional[int] = None, detail: Optional[str] = None) -> Dict[str, Any]:
    data: Dict[str, Any] = {"status": status, "ts": int(time.time())}
    if percent is not None:
        data["percent"] = percent
    if eta is not None:
        data["eta"] = eta
    if detail:
        data["detail"] = detail
    if _redis:
        try:
            _redis.setex(f"task:{task_id}", 3600, json.dumps(data))
        except Exception:
            # Redis not available; disable for this process to avoid repeated errors
            try:
                _redis.close()  # type: ignore[attr-defined]
            except Exception:
                pass
            globals()["_redis"] = None
    return data


def get_progress(task_id: str) -> Optional[Dict[str, Any]]:
    if _redis:
        try:
            raw = _redis.get(f"task:{task_id}")
        except Exception:
            # Redis connection failed; turn off and fall back to None
            try:
                _redis.close()  # type: ignore[attr-defined]
            except Exception:
                pass
            globals()["_redis"] = None
            return None
        if raw:
            try:
                return json.loads(raw)
            except Exception:
                return None
    return None