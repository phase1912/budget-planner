"""Security utilities for password hashing and basic tokens (F1.1.2)."""

import base64
import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.core.config import get_settings

if TYPE_CHECKING:
    from cryptography.fernet import Fernet


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


def create_access_token(
    subject: str | Any, expires_delta: timedelta | None = None, *, second_factor: bool = False
) -> str:
    """Create a JWT access token (F1.2.1).

    `second_factor` says the session was opened with an authenticator code too (F18.6.1):
    what the admin pages ask for.
    """
    settings = get_settings()
    now = datetime.now(UTC)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.access_token_expire_minutes)

    to_encode = {"exp": expire, "iat": now, "sub": str(subject), "sf": second_factor}

    encoded_jwt = jwt.encode(
        to_encode, settings.jwt_secret_key.get_secret_value(), algorithm="HS256"
    )
    return encoded_jwt


def create_refresh_token() -> str:
    """Create a random refresh token string (F1.2.2)."""
    return secrets.token_urlsafe(32)


def create_link_token(purpose: str, subject: str, ttl: timedelta, **claims: str) -> str:
    """Sign a link a letter carries: what it is for, whose it is, until when (F17.8).

    `claims` bind the link to the account's state when it was sent — the address, a
    fingerprint of the password — so it stops working once that state changes, which
    is what makes it single-use without a table of spent links.
    """
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {"purpose": purpose, "sub": subject, "iat": now, "exp": now + ttl, **claims}
    return jwt.encode(payload, settings.jwt_secret_key.get_secret_value(), algorithm="HS256")


def read_link_token(token: str, purpose: str) -> dict[str, Any] | None:
    """The claims of a valid, unexpired link made for `purpose`, else None."""
    settings = get_settings()
    try:
        payload: dict[str, Any] = jwt.decode(
            token, settings.jwt_secret_key.get_secret_value(), algorithms=["HS256"]
        )
    except jwt.InvalidTokenError:
        return None
    return payload if payload.get("purpose") == purpose else None


def fingerprint(secret: str) -> str:
    """A short, one-way digest of a stored secret, to bind a link to its current value."""
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()[:16]


def _secret_box() -> "Fernet":
    """The key secrets kept in the database are encrypted with, derived from the JWT key.

    Rotating JWT_SECRET_KEY therefore also voids every authenticator set up so far: the
    users affected set theirs up again (ADR-0021).
    """
    from cryptography.fernet import Fernet

    key = hashlib.sha256(
        b"two-factor:" + get_settings().jwt_secret_key.get_secret_value().encode()
    ).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def encrypt_secret(plain: str) -> str:
    """Encrypt a secret before it is stored (the authenticator's, F18.6.1)."""
    return _secret_box().encrypt(plain.encode()).decode()


def decrypt_secret(stored: str) -> str:
    """The secret `encrypt_secret` stored."""
    return _secret_box().decrypt(stored.encode()).decode()
