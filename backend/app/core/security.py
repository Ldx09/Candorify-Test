from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import settings


def hash_password(password: str) -> str:
    """Turns a plain password into a bcrypt hash. Only the hash is ever stored."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def token_lifetime(remember_me: bool) -> timedelta:
    """About a day normally; about 30 days with "keep me signed in"."""
    return timedelta(days=settings.REMEMBER_ME_DAYS) if remember_me else timedelta(hours=settings.SESSION_HOURS)


def create_access_token(user_id: int, remember_me: bool = False) -> tuple[str, datetime]:
    """Returns (token, expiry time)."""
    expires = datetime.now(timezone.utc) + token_lifetime(remember_me)
    payload = {"sub": str(user_id), "exp": expires}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM), expires


def decode_access_token(token: str) -> int | None:
    """Returns the user id inside a valid token, or None if the token is invalid or expired."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        return int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        return None