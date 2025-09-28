from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from jose import jwt, JWTError
from passlib.context import CryptContext

from .settings import get_settings


# Use bcrypt_sha256 to support passwords longer than 72 bytes safely.
pwd_context = CryptContext(schemes=["bcrypt_sha256"], deprecated="auto")


def hash_password(plain: str) -> str:
    hashed: str = pwd_context.hash(plain)
    return hashed


def verify_password(plain: str, hashed: str) -> bool:
    ok: bool = pwd_context.verify(plain, hashed)
    return ok


def create_access_token(subject: str, extra: Dict[str, Any] | None = None) -> tuple[str, int]:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=settings.access_token_exp_minutes)
    payload: Dict[str, Any] = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    if extra:
        payload.update(extra)
    token = jwt.encode(payload, settings.secret_key, algorithm="HS256")
    return token, int((exp - now).total_seconds())


def decode_access_token(token: str) -> Dict[str, Any]:
    settings = get_settings()
    try:
        data: Dict[str, Any] = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        return data
    except JWTError as exc:  # noqa: PERF203
        raise ValueError("Invalid token") from exc
