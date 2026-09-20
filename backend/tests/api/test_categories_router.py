import uuid
from collections.abc import AsyncGenerator
from decimal import Decimal
from typing import Any

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.db.session import get_db_session
from app.main import create_app
from app.models.category import Category
from app.models.line_item import LineItem
from app.models.receipt import Receipt
from app.models.user import User


@pytest.fixture
def app() -> FastAPI:
    """Create a fresh FastAPI application for each test."""
    return create_app()


@pytest.mark.asyncio
async def test_list_categories_returns_built_in_categories(
    app: FastAPI,
    db_session: AsyncSession,
) -> None:
    """The categories endpoint returns the default built-in categories."""
    built_ins = [
        Category(name="Groceries"),
        Category(name="Dining"),
    ]
    db_session.add_all(built_ins)
    await db_session.flush()

    user = User(
        id=uuid.uuid4(),
        email="test@test.com",
        first_name="A",
        last_name="B",
        password_hash="hash",
    )

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db_session] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/categories")
    assert response.status_code == 200

    data: list[dict[str, Any]] = response.json()
    assert len(data) >= 2
    names = {c["name"] for c in data}
    assert "Groceries" in names
    assert "Dining" in names

    groceries = next(c for c in data if c["name"] == "Groceries")
    assert groceries["is_builtin"] is True
    assert groceries["item_count"] == 0
    assert Decimal(str(groceries["total_amount"])) == Decimal("0.00")


@pytest.mark.asyncio
async def test_list_categories_aggregates_current_user_items_only(
    app: FastAPI,
    db_session: AsyncSession,
) -> None:
    """The endpoint aggregates item_count and total_amount for the user's line items."""
    cat = Category(name="Test Category")

    current_user_db = User(
        email="current@test.com",
        first_name="C",
        last_name="U",
        password_hash="hash",
    )
    other_user = User(
        email="other@test.com",
        first_name="O",
        last_name="U",
        password_hash="hash",
    )

    db_session.add_all([cat, current_user_db, other_user])
    await db_session.flush()

    # Current user's receipt and items
    receipt = Receipt(user_id=current_user_db.id, status="PARSED")
    db_session.add(receipt)
    await db_session.flush()

    item1 = LineItem(
        receipt_id=receipt.id,
        name="Bus",
        quantity=Decimal("1"),
        unit_price=Decimal("2.50"),
        total_price=Decimal("2.50"),
        category_id=cat.id,
    )
    item2 = LineItem(
        receipt_id=receipt.id,
        name="Train",
        quantity=Decimal("1"),
        unit_price=Decimal("5.00"),
        total_price=Decimal("5.00"),
        category_id=cat.id,
    )

    # Other user's receipt and item — must not be counted
    other_receipt = Receipt(user_id=other_user.id, status="PARSED")
    db_session.add(other_receipt)
    await db_session.flush()

    other_item = LineItem(
        receipt_id=other_receipt.id,
        name="Taxi",
        quantity=Decimal("1"),
        unit_price=Decimal("10.00"),
        total_price=Decimal("10.00"),
        category_id=cat.id,
    )

    db_session.add_all([item1, item2, other_item])
    await db_session.flush()

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_current_user] = lambda: current_user_db
    app.dependency_overrides[get_db_session] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/categories")
    assert response.status_code == 200

    data: list[dict[str, Any]] = response.json()
    result = next(c for c in data if c["name"] == "Test Category")

    # Only current user's 2 items should be counted
    assert result["item_count"] == 2
    assert Decimal(str(result["total_amount"])) == Decimal("7.50")
