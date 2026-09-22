"""安全：密码哈希 + JWT。为避免强依赖 bcrypt/passlib 的环境问题，密码用 pbkdf2 哈希。"""
from __future__ import annotations
import hashlib
import hmac
import base64
import json
import time
from app.config import settings


def hash_password(raw: str) -> str:
    salt = hashlib.sha256((raw + settings.SECRET_KEY).encode()).hexdigest()[:16]
    dk = hashlib.pbkdf2_hmac("sha256", raw.encode(), salt.encode(), 100_000)
    return f"pbkdf2${salt}${dk.hex()}"


def verify_password(raw: str, stored: str) -> bool:
    try:
        _, salt, hexed = stored.split("$")
        dk = hashlib.pbkdf2_hmac("sha256", raw.encode(), salt.encode(), 100_000)
        return hmac.compare_digest(dk.hex(), hexed)
    except Exception:
        return False


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _unb64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def create_token(sub: str, role: str = "admin") -> str:
    header = _b64(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    payload = {"sub": sub, "role": role,
               "exp": int(time.time()) + settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60}
    body = _b64(json.dumps(payload).encode())
    sig = _sign(f"{header}.{body}")
    return f"{header}.{body}.{sig}"


def _sign(msg: str) -> str:
    return _b64(hmac.new(settings.SECRET_KEY.encode(), msg.encode(), hashlib.sha256).digest())


def decode_token(token: str) -> dict | None:
    try:
        header, body, sig = token.split(".")
        if not hmac.compare_digest(_sign(f"{header}.{body}"), sig):
            return None
        payload = json.loads(_unb64(body))
        if payload.get("exp", 0) < time.time():
            return None
        return payload
    except Exception:
        return None
