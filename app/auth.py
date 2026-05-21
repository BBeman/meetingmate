from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from app.config import get_settings


def hash_password(plain_password: str) -> str:
    """Hash a plain text password using bcrypt."""
    password_bytes = plain_password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Check a plain password against its hash."""
    password_bytes = plain_password.encode("utf-8")
    hashed_bytes = hashed_password.encode("utf-8")
    return bcrypt.checkpw(password_bytes, hashed_bytes)


def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    """Create a signed JWT with the given subject (typically user id or email)."""
    settings = get_settings()

    if not settings.jwt_secret:
        raise ValueError("JWT_SECRET must be set in environment")

    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.jwt_expire_minutes)

    expire = datetime.now(timezone.utc) + expires_delta
    payload = {"sub": subject, "exp": expire}

    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def verify_token(token: str) -> str | None:
    """Verify a JWT and return the subject if valid, None otherwise."""
    settings = get_settings()

    if not settings.jwt_secret:
        raise ValueError("JWT_SECRET must be set in environment")

    try:
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        subject: str | None = payload.get("sub")
        return subject
    except JWTError:
        return None
