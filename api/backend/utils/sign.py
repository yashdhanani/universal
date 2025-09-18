import base64
import hashlib
import hmac
import json
import time
from typing import Dict

def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")

def b64url_decode(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)

def sign_payload(secret: str, payload: Dict) -> str:
    body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    sig = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).digest()
    return f"{b64url(body)}.{b64url(sig)}"

def verify_token(secret: str, token: str) -> Dict:
    try:
        body_b64, sig_b64 = token.split(".", 1)
        body = b64url_decode(body_b64)
        sig = b64url_decode(sig_b64)
        good = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).digest()
        if not hmac.compare_digest(sig, good):
            raise ValueError("bad signature")
        data = json.loads(body.decode("utf-8"))
        exp = int(data.get("exp", 0))
        if exp and time.time() > exp:
            raise ValueError("expired")
        return data
    except Exception as e:
        raise ValueError(f"invalid token: {e}")

def make_token(secret: str, data: Dict, ttl_sec: int = 600) -> str:
    payload = dict(data)
    payload["exp"] = int(time.time()) + int(ttl_sec)
    return sign_payload(secret, payload)
