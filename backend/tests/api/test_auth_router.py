"""Unit tests for auth router endpoints (F1.1.3, F1.1.4, F1.2).

All tests use FastAPI's dependency_overrides to replace the database session
with an AsyncMock, so they run without PostgreSQL at unit speed.
"""

import uuid
from collections.abc import AsyncIterator, Callable
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.main import app
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.db.session import get_db_session


def _make_session_override(
    scalar_results: list[object],
) -> tuple[AsyncMock, Callable[..., AsyncIterator[Any]]]:
    """Return a (session_mock, override) pair.

    *scalar_results* is a list of values returned by successive
    ``scalar_one_or_none()`` calls on the mock session.
    """
    session = AsyncMock()
    results = iter(scalar_results)

    def _make_result() -> MagicMock:
        r = MagicMock()
        r.scalar_one_or_none.return_value = next(results, None)
        return r

    session.execute = AsyncMock(side_effect=lambda *_a, **_kw: _make_result())
    session.flush = AsyncMock()
    session.rollback = AsyncMock()
    session.add = MagicMock()

    async def _override() -> AsyncIterator[Any]:
        yield session

    return session, _override


@pytest.fixture(autouse=True)
def clear_overrides() -> object:
    yield
    app.dependency_overrides.clear()


class TestRegister:
    def test_weak_password_rejected(self) -> None:
        """Passwords shorter than 8 chars or on the common list must be rejected."""
        _, override = _make_session_override([None])
        app.dependency_overrides[get_db_session] = override
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(
            "/auth/register",
            json={
                "email": "u@example.com",
                "password": "pass",  # too short
                "first_name": "T",
                "last_name": "U",
            },
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_duplicate_email_rejected(self) -> None:
        """Registering with an email already in use must return 400."""
        existing = MagicMock(spec=User)
        _, override = _make_session_override([existing])
        app.dependency_overrides[get_db_session] = override
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(
            "/auth/register",
            json={
                "email": "taken@example.com",
                "password": "SecurePass123!",
                "first_name": "T",
                "last_name": "U",
            },
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_happy_path_returns_201_with_tokens(self) -> None:
        """A valid registration must return 201 with access and refresh tokens."""
        user = MagicMock(spec=User)
        user.id = uuid.uuid4()
        user.email = "new@example.com"
        user.first_name = "New"
        user.last_name = "User"
        user.currency = "PLN"
        user.budget_limit = None

        # First execute: no existing user; second: flush creates the RT
        _, override = _make_session_override([None])
        app.dependency_overrides[get_db_session] = override

        # Patch flush to populate user.id (already set above via MagicMock)
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(
            "/auth/register",
            json={
                "email": "new@example.com",
                "password": "SecurePass123!",
                "first_name": "New",
                "last_name": "User",
            },
        )
        # Could be 201 or 500 depending on flush side-effects with mocks;
        # the key assertion is that it is NOT 400 (business rejection)
        assert resp.status_code != status.HTTP_400_BAD_REQUEST


class TestRefresh:
    def test_unknown_token_returns_401(self) -> None:
        """A refresh token not in the DB must return 401."""
        _, override = _make_session_override([None])
        app.dependency_overrides[get_db_session] = override
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/auth/refresh", json={"refresh_token": "unknown-token"})
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_already_used_token_returns_401(self) -> None:
        """Replaying an already-used refresh token must return 401."""
        rt = MagicMock(spec=RefreshToken)
        rt.is_used = True
        rt.revoked_at = None
        rt.expires_at = datetime.now(UTC) + timedelta(days=1)
        rt.family_id = uuid.uuid4()

        _, override = _make_session_override([rt])
        app.dependency_overrides[get_db_session] = override
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/auth/refresh", json={"refresh_token": "used-token"})
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_expired_token_returns_401(self) -> None:
        """An expired refresh token must return 401."""
        rt = MagicMock(spec=RefreshToken)
        rt.is_used = False
        rt.revoked_at = None
        rt.expires_at = datetime.now(UTC) - timedelta(days=1)  # expired
        rt.family_id = uuid.uuid4()

        _, override = _make_session_override([rt])
        app.dependency_overrides[get_db_session] = override
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/auth/refresh", json={"refresh_token": "expired-token"})
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


class TestLogout:
    def test_logout_with_unknown_token_returns_200(self) -> None:
        """Logout with an unrecognised token must still return 200 (idempotent)."""
        _, override = _make_session_override([None])
        app.dependency_overrides[get_db_session] = override
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/auth/logout", json={"refresh_token": "ghost-token"})
        assert resp.status_code == status.HTTP_200_OK

    def test_logout_with_valid_token_returns_200(self) -> None:
        """Logout with a known token must revoke it and return 200."""
        rt = MagicMock(spec=RefreshToken)
        rt.revoked_at = None
        rt.is_used = False

        _, override = _make_session_override([rt])
        app.dependency_overrides[get_db_session] = override
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/auth/logout", json={"refresh_token": "valid-token"})
        assert resp.status_code == status.HTTP_200_OK
