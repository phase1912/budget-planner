from collections.abc import AsyncGenerator
from decimal import Decimal
from typing import Any

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.db.session import get_db_session
from app.domain.categories import DEFAULT_CATEGORY_ORDER
from app.main import create_app
from app.models.category import Category
from app.models.user import User
from tests.factories.category import CategoryFactory
from tests.factories.line_item import LineItemFactory
from tests.factories.receipt import ReceiptFactory
from tests.factories.user import UserFactory


@pytest.fixture
def app() -> FastAPI:
    """Create a fresh FastAPI application for each test."""
    return create_app()


async def _get_categories(app: FastAPI, session: AsyncSession, user: User) -> list[dict[str, Any]]:
    """Call the endpoint as `user`, sharing the test's transaction."""

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield session

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db_session] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/categories")

    assert response.status_code == 200
    data: list[dict[str, Any]] = response.json()
    return data


async def _built_in(session: AsyncSession, name: str) -> Category:
    """Fetch a seeded default category by name (migration `c7dfee8c1b06`)."""
    stmt = select(Category).where(Category.name == name, Category.user_id.is_(None))
    return (await session.execute(stmt)).scalar_one()


@pytest.mark.asyncio
async def test_built_in_categories_are_listed_in_the_taxonomy_order(
    app: FastAPI,
    db_session: AsyncSession,
) -> None:
    """The seeded defaults come back in the BRD's order, not alphabetically (BRD C1)."""
    user = await UserFactory.create_async()

    data = await _get_categories(app, db_session, user)

    assert [category["name"] for category in data] == list(DEFAULT_CATEGORY_ORDER)
    assert all(category["is_builtin"] for category in data)


@pytest.mark.asyncio
async def test_custom_categories_follow_the_built_in_ones(
    app: FastAPI,
    db_session: AsyncSession,
) -> None:
    """A user's own categories are a separate, alphabetical section (BRD C6)."""
    user = await UserFactory.create_async()
    await CategoryFactory.create_async(name="Pet Supplies", user_id=user.id)
    await CategoryFactory.create_async(name="Kids & school", user_id=user.id)

    data = await _get_categories(app, db_session, user)

    assert [category["name"] for category in data] == [
        *DEFAULT_CATEGORY_ORDER,
        "Kids & school",
        "Pet Supplies",
    ]
    assert [category["is_builtin"] for category in data[-2:]] == [False, False]


@pytest.mark.asyncio
async def test_a_category_with_nothing_filed_under_it_reports_zero(
    app: FastAPI,
    db_session: AsyncSession,
) -> None:
    """An unused category still appears, rather than vanishing from the taxonomy."""
    user = await UserFactory.create_async()

    data = await _get_categories(app, db_session, user)

    groceries = next(c for c in data if c["name"] == "Groceries")
    assert groceries["item_count"] == 0
    assert Decimal(str(groceries["total_amount"])) == Decimal("0")


@pytest.mark.asyncio
async def test_totals_count_only_the_current_users_items(
    app: FastAPI,
    db_session: AsyncSession,
) -> None:
    """A built-in category reports this user's spending, never everyone's (BRD N2)."""
    transport = await _built_in(db_session, "Transport")
    current_user = await UserFactory.create_async()
    other_user = await UserFactory.create_async()

    own_receipt = await ReceiptFactory.create_async(user_id=current_user.id)
    for amount in ("2.50", "5.00"):
        await LineItemFactory.create_async(
            receipt=own_receipt,
            category=transport,
            total_price=Decimal(amount),
        )

    other_receipt = await ReceiptFactory.create_async(user_id=other_user.id)
    await LineItemFactory.create_async(
        receipt=other_receipt,
        category=transport,
        total_price=Decimal("10.00"),
    )

    data = await _get_categories(app, db_session, current_user)

    row = next(c for c in data if c["name"] == "Transport")
    assert row["item_count"] == 2
    assert Decimal(str(row["total_amount"])) == Decimal("7.50")


@pytest.mark.asyncio
async def test_another_users_custom_category_is_not_listed(
    app: FastAPI,
    db_session: AsyncSession,
) -> None:
    """One user's taxonomy never leaks into another's (BRD N2, C6)."""
    current_user = await UserFactory.create_async()
    other_user = await UserFactory.create_async()
    await CategoryFactory.create_async(name="Wine Cellar", user_id=other_user.id)

    data = await _get_categories(app, db_session, current_user)

    assert "Wine Cellar" not in {category["name"] for category in data}
    assert [category["name"] for category in data] == list(DEFAULT_CATEGORY_ORDER)


@pytest.mark.asyncio
async def test_listing_categories_requires_authentication(app: FastAPI) -> None:
    """The taxonomy is per-user, so an anonymous caller gets nothing (BRD N2)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/categories")

    assert response.status_code == 401
