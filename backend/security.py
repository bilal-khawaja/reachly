import os
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

import db  # noqa: F401  (loads .env)


def _secret() -> str:
    key = os.getenv("SECRET_KEY")
    if not key or len(key) < 32:
        raise RuntimeError("SECRET_KEY missing or too short (>=32 chars); see .env.example")
    return key


def algorithm() -> str:
    return os.getenv("ALGORITHM", "HS256")


def expire_minutes() -> int:
    return int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))


def session_max_days() -> int:
    return int(os.getenv("SESSION_MAX_DAYS", "7"))


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except ValueError:
        return False


def create_access_token(
    subject: str, expires: timedelta | None = None, *, ver: int = 0, auth_time: datetime | None = None
) -> str:
    """auth = when the user really logged in (kept across renewals, enforces the absolute cap); ver = users.token_version."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "iat": now,
        "exp": now + (expires or timedelta(minutes=expire_minutes())),
        "auth": int((auth_time or now).timestamp()),
        "ver": ver,
    }
    return jwt.encode(payload, _secret(), algorithm=algorithm())


def decode_token(token: str) -> dict:
    """Raises jwt.PyJWTError on bad signature / expiry."""
    return jwt.decode(token, _secret(), algorithms=[algorithm()], options={"require": ["exp", "sub"]})
