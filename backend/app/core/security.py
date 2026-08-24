"""Security utilities for password hashing and basic tokens (F1.1.2)."""

import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.core.config import get_settings


def _get_hasher() -> PasswordHasher:
    settings = get_settings()
    return PasswordHasher(
        time_cost=settings.argon2_time_cost,
        memory_cost=settings.argon2_memory_cost,
        parallelism=settings.argon2_parallelism,
    )


_DUMMY_HASH: str | None = None


def get_dummy_hash() -> str:
    """Return a dummy hash to mitigate timing attacks.
    Computed lazily so settings aren't required at module import time.
    """
    global _DUMMY_HASH
    if _DUMMY_HASH is None:
        _DUMMY_HASH = _get_hasher().hash("dummy-password-for-timing-attack-mitigation")
    return _DUMMY_HASH


def get_password_hash(password: str) -> str:
    """Hash a password using Argon2id."""
    return _get_hasher().hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against an Argon2id hash."""
    try:
        return _get_hasher().verify(hashed_password, plain_password)
    except VerifyMismatchError:
        return False


def create_access_token(subject: str | Any, expires_delta: timedelta | None = None) -> str:
    """Create a JWT access token (F1.2.1)."""
    settings = get_settings()
    now = datetime.now(UTC)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.access_token_expire_minutes)

    to_encode = {"exp": expire, "iat": now, "sub": str(subject)}

    encoded_jwt = jwt.encode(
        to_encode, settings.jwt_secret_key.get_secret_value(), algorithm="HS256"
    )
    return encoded_jwt


def create_refresh_token() -> str:
    """Create a random refresh token string (F1.2.2)."""
    return secrets.token_urlsafe(32)
