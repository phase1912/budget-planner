import uuid
from collections.abc import AsyncIterator, Callable
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.api.dependencies import get_current_user
from app.db.session import get_db_session
from app.main import app
from app.models.user import User


def _make_session_override() -> tuple[AsyncMock, Callable[..., AsyncIterator[Any]]]:
    session = AsyncMock()
    session.execute = AsyncMock()
    session.flush = AsyncMock()
    session.rollback = AsyncMock()
    session.commit = AsyncMock()
    session.add = MagicMock()

    # mock begin_nested as an async context manager
    nested_cm = AsyncMock()
    nested_cm.__aenter__.return_value = None
    nested_cm.__aexit__.return_value = None
    session.begin_nested = MagicMock(return_value=nested_cm)

    async def _override() -> AsyncIterator[Any]:
        yield session

    return session, _override


@pytest.fixture(autouse=True)
def clear_overrides() -> object:
    yield
    app.dependency_overrides.clear()


def _mock_user() -> User:
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.email = "test@example.com"
    user.first_name = "Test"
    user.last_name = "User"
    user.currency = "USD"
    user.budget_limit = None
    return user


def _override_auth(user: User) -> None:
    async def _get_user() -> User:
        return user

    app.dependency_overrides[get_current_user] = _get_user


class TestUsersRouter:
    def test_get_me(self) -> None:
        user = _mock_user()
        _override_auth(user)
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/users/me")
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["email"] == "test@example.com"
        assert data["currency"] == "USD"

    def test_update_me(self) -> None:
        user = _mock_user()
        _override_auth(user)
        session, override = _make_session_override()
        app.dependency_overrides[get_db_session] = override

        result_mock = MagicMock()
        result_mock.scalar.return_value = None
        session.execute.return_value = result_mock

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.patch("/users/me", json={"currency": "EUR", "budget_limit": "500.00"})
        assert resp.status_code == status.HTTP_200_OK

    def test_update_me_receipts_exist_fails(self) -> None:
        user = _mock_user()
        _override_auth(user)
        session, override = _make_session_override()
        app.dependency_overrides[get_db_session] = override

        result_mock = MagicMock()
        result_mock.scalar.return_value = 1
        session.execute.return_value = result_mock

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.patch("/users/me", json={"currency": "EUR"})
        assert resp.status_code == status.HTTP_409_CONFLICT
        assert resp.json()["detail"] == "Cannot change currency once receipts exist."
