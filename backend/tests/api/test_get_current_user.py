"""Unit tests for the get_current_user dependency (F1.2.4).

All branches of the dependency are exercised without a real database:
the SQLAlchemy session is replaced with an AsyncMock so these tests run
at unit speed and do not require PostgreSQL.
"""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import jwt
import pytest
from fastapi.security import HTTPAuthorizationCredentials

from app.api.dependencies import get_current_user
from app.core.config import get_settings
from app.api.errors import AuthenticationError
from app.models.user import User


def _make_token(subject: str, expired: bool = False) -> str:
    """Return a signed JWT for the given subject."""
    settings = get_settings()
    now = datetime.now(UTC)
    delta = timedelta(minutes=-5) if expired else timedelta(minutes=15)
    payload = {"sub": subject, "iat": now, "exp": now + delta}
    return jwt.encode(payload, settings.jwt_secret_key.get_secret_value(), algorithm="HS256")


def _mock_session(user: User | None) -> AsyncMock:
    """Return an AsyncSession mock whose scalar_one_or_none() returns *user*."""
    session = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = user
    session.execute = AsyncMock(return_value=result)
    return session


@pytest.mark.asyncio
async def test_get_current_user_no_credentials_raises() -> None:
    """Missing Authorization header must raise AuthenticationError."""
    session = _mock_session(None)
    with pytest.raises(AuthenticationError, match="Not authenticated"):
        await get_current_user(credentials=None, session=session)


@pytest.mark.asyncio
async def test_get_current_user_expired_token_raises() -> None:
    """An expired JWT must raise AuthenticationError."""
    token = _make_token(str(uuid.uuid4()), expired=True)
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    session = _mock_session(None)
    with pytest.raises(AuthenticationError, match="Token expired"):
        await get_current_user(credentials=credentials, session=session)


@pytest.mark.asyncio
async def test_get_current_user_invalid_token_raises() -> None:
    """A tampered / garbage JWT must raise AuthenticationError."""
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="not.a.jwt")
    session = _mock_session(None)
    with pytest.raises(AuthenticationError, match="Invalid token"):
        await get_current_user(credentials=credentials, session=session)


@pytest.mark.asyncio
async def test_get_current_user_missing_sub_raises() -> None:
    """A valid JWT without a 'sub' claim must raise AuthenticationError."""
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {"iat": now, "exp": now + timedelta(minutes=15)}  # no sub
    token = jwt.encode(payload, settings.jwt_secret_key.get_secret_value(), algorithm="HS256")
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    session = _mock_session(None)
    with pytest.raises(AuthenticationError, match="Invalid token"):
        await get_current_user(credentials=credentials, session=session)


@pytest.mark.asyncio
async def test_get_current_user_user_not_found_raises() -> None:
    """A valid JWT whose user no longer exists in DB must raise AuthenticationError."""
    user_id = uuid.uuid4()
    token = _make_token(str(user_id))
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    session = _mock_session(None)  # DB returns None
    with pytest.raises(AuthenticationError, match="User not found"):
        await get_current_user(credentials=credentials, session=session)


@pytest.mark.asyncio
async def test_get_current_user_happy_path_returns_user() -> None:
    """A valid JWT matching an existing user must return that user."""
    user_id = uuid.uuid4()
    mock_user = MagicMock(spec=User)
    mock_user.id = user_id

    token = _make_token(str(user_id))
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    session = _mock_session(mock_user)

    result = await get_current_user(credentials=credentials, session=session)
    assert result is mock_user


@pytest.mark.asyncio
async def test_get_current_user_invalid_uuid_in_sub_raises() -> None:
    """A JWT whose sub is a non-UUID string must raise AuthenticationError (line 45-46)."""
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {"sub": "not-a-uuid", "iat": now, "exp": now + timedelta(minutes=15)}
    token = jwt.encode(payload, settings.jwt_secret_key.get_secret_value(), algorithm="HS256")
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    session = _mock_session(None)
    with pytest.raises(AuthenticationError, match="Invalid user ID in token"):
        await get_current_user(credentials=credentials, session=session)
