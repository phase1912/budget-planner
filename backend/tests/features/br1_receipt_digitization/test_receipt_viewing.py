import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, patch

import jwt
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pytest_bdd import given, parsers, scenarios, then, when

from app.api.dependencies import get_current_user
from app.core.config import get_settings
from app.main import create_app
from app.models.receipt import Receipt
from app.models.user import User

scenarios("receipt_viewing.feature")


@pytest.fixture
def mock_repo():
    with patch("app.api.routers.receipts.ReceiptRepository") as mock:
        instance = mock.return_value
        yield instance


@pytest.fixture
def test_app() -> FastAPI:
    from app.db.session import get_db_session
    app = create_app()
    app.dependency_overrides[get_db_session] = lambda: AsyncMock()
    return app


@pytest.fixture
def client(test_app: FastAPI) -> TestClient:
    return TestClient(test_app, follow_redirects=False)


@pytest.fixture
def state() -> dict[str, Any]:
    return {"receipts": []}


@given("the user is logged in")
def the_user_is_logged_in(test_app: FastAPI, client: TestClient, state: dict[str, Any]) -> None:
    user = User(
        id=uuid.uuid4(),
        email="viewer@test.com",
        first_name="V",
        last_name="V",
    )
    test_app.dependency_overrides[get_current_user] = lambda: user

    settings = get_settings()
    token = jwt.encode(
        {"sub": str(user.id)}, settings.jwt_secret_key.get_secret_value(), algorithm="HS256"
    )
    client.headers["Authorization"] = f"Bearer {token}"

    state["logged_in_user"] = user


@given(parsers.parse("the user has {count:d} stored receipts"))
def user_has_receipts(state: dict[str, Any], count: int) -> None:
    now = datetime.now(UTC)
    user = state["logged_in_user"]
    for i in range(count):
        r = Receipt(
            id=uuid.uuid4(),
            user_id=user.id,
            merchant_name=f"Merchant {i}",
            transaction_date=now - timedelta(days=i),
            total_amount=10.0 + i,
            status="parsed",
            file_ids=["file-1"],
            line_items=[],
        )
        r.created_at = now - timedelta(days=i)
        state["receipts"].append(r)


@when(parsers.parse("the user requests the first page of receipts with a limit of {limit:d}"))
def request_receipts(client: TestClient, limit: int, state: dict[str, Any], mock_repo: AsyncMock) -> None:
    mock_repo.list_paginated = AsyncMock(return_value=(state["receipts"][:limit], len(state["receipts"])))
    state["response"] = client.get(f"/receipts?page=1&size={limit}")


@then(parsers.parse("the agent should return exactly {count:d} receipts"))
def check_receipt_count(state: dict[str, Any], count: int) -> None:
    resp = state["response"]
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == count


@then(parsers.parse("the total count of receipts should be {count:d}"))
def check_total_count(state: dict[str, Any], count: int) -> None:
    resp = state["response"]
    data = resp.json()
    assert data["total"] == count


@then("the receipts should be ordered by date descending")
def check_ordering(state: dict[str, Any]) -> None:
    resp = state["response"]
    data = resp.json()
    items = data["items"]
    for i in range(len(items) - 1):
        # We mocked it correctly by date descending in our fake setup
        assert items[i]["transaction_date"] >= items[i + 1]["transaction_date"]


@given("another user has a stored receipt")
def other_user_receipt(state: dict[str, Any]) -> None:
    other_user = User(id=uuid.uuid4(), email="other@test.com")
    r = Receipt(
        id=uuid.uuid4(),
        user_id=other_user.id,
        merchant_name="Secret Store",
        transaction_date=datetime.now(UTC),
        total_amount=100.0,
        status="parsed",
        file_ids=["file-2"],
        line_items=[],
    )
    r.created_at = datetime.now(UTC)
    state["other_receipt_id"] = str(r.id)
    # Don't add it to state["receipts"] since the current user shouldn't see it


@when("the user requests the details for the other user's receipt")
def request_other_receipt(client: TestClient, state: dict[str, Any], mock_repo: AsyncMock) -> None:
    receipt_id = state["other_receipt_id"]
    mock_repo.get_with_items = AsyncMock(return_value=None)
    state["response"] = client.get(f"/receipts/{receipt_id}")


@then('the agent should return a "not found" error')
def check_not_found(state: dict[str, Any]) -> None:
    resp = state["response"]
    assert resp.status_code == 404
    assert resp.json()["code"] == "not_found"
