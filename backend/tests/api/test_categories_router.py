import uuid
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
from app.domain.categories import DEFAULT_CATEGORY_ORDER, UNCATEGORIZED
from app.main import create_app
from app.models.category import Category
from app.models.user import User
from app.repository.category import CategoryRepository
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


async def _as(app: FastAPI, session: AsyncSession, user: User) -> AsyncClient:
    """An HTTP client acting as `user`, sharing the test's transaction."""

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield session

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db_session] = override_get_db
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.asyncio
async def test_a_new_category_is_offered_at_once_for_manual_and_automatic_filing(
    app: FastAPI, db_session: AsyncSession
) -> None:
    """C6: "available for both manual and automatic assignment" the moment it exists."""
    user = await UserFactory.create_async()
    async with await _as(app, db_session, user) as client:
        response = await client.post("/api/v1/categories", json={"name": "  Pet Supplies "})

    assert response.status_code == 201
    body = response.json()
    assert (body["name"], body["is_builtin"], body["item_count"]) == ("Pet Supplies", False, 0)
    available = await CategoryRepository(db_session).list_available(user.id)
    assert "Pet Supplies" in [category.name for category in available]


@pytest.mark.asyncio
@pytest.mark.parametrize("name", ["groceries", "PET SUPPLIES"])
async def test_a_name_already_in_the_taxonomy_is_refused(
    app: FastAPI, db_session: AsyncSession, name: str
) -> None:
    """Two buckets with one name could not be told apart in the picker."""
    user = await UserFactory.create_async()
    await _built_in(db_session, "Groceries")
    await CategoryFactory.create_async(name="Pet Supplies", user_id=user.id)

    async with await _as(app, db_session, user) as client:
        response = await client.post("/api/v1/categories", json={"name": name})

    assert response.status_code == 409
    assert response.json()["code"] == "domain_error"


@pytest.mark.asyncio
async def test_another_users_category_name_is_free_to_use(
    app: FastAPI, db_session: AsyncSession
) -> None:
    user, other = await UserFactory.create_async(), await UserFactory.create_async()
    await CategoryFactory.create_async(name="Pet Supplies", user_id=other.id)

    async with await _as(app, db_session, user) as client:
        response = await client.post("/api/v1/categories", json={"name": "Pet Supplies"})

    assert response.status_code == 201


@pytest.mark.asyncio
@pytest.mark.parametrize("name", ["", "   ", "x" * 101])
async def test_a_blank_or_overlong_name_is_rejected(
    app: FastAPI, db_session: AsyncSession, name: str
) -> None:
    user = await UserFactory.create_async()
    async with await _as(app, db_session, user) as client:
        response = await client.post("/api/v1/categories", json={"name": name})

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_renaming_keeps_the_items_filed_under_it(
    app: FastAPI, db_session: AsyncSession
) -> None:
    user = await UserFactory.create_async()
    pets = await CategoryFactory.create_async(name="Pets", user_id=user.id)
    receipt = await ReceiptFactory.create_async(user_id=user.id)
    await LineItemFactory.create_async(receipt=receipt, category=pets, total_price=Decimal("9.99"))

    async with await _as(app, db_session, user) as client:
        response = await client.patch(
            f"/api/v1/categories/{pets.id}", json={"name": "Pet Supplies"}
        )

    assert response.status_code == 200
    body = response.json()
    assert (body["name"], body["item_count"]) == ("Pet Supplies", 1)


@pytest.mark.asyncio
async def test_a_built_in_or_another_users_category_cannot_be_renamed(
    app: FastAPI, db_session: AsyncSession
) -> None:
    user, other = await UserFactory.create_async(), await UserFactory.create_async()
    groceries = await _built_in(db_session, "Groceries")
    theirs = await CategoryFactory.create_async(name="Theirs", user_id=other.id)

    async with await _as(app, db_session, user) as client:
        for category in (groceries, theirs):
            response = await client.patch(
                f"/api/v1/categories/{category.id}", json={"name": "Mine now"}
            )
            assert response.status_code == 404


@pytest.mark.asyncio
async def test_deleting_a_category_moves_its_items_and_rules_where_the_user_chose(
    app: FastAPI, db_session: AsyncSession
) -> None:
    """The F5.6 demo: create "Pet Supplies", file items, delete it, choose where they land."""
    user = await UserFactory.create_async()
    other = await _built_in(db_session, "Other")
    async with await _as(app, db_session, user) as client:
        created = await client.post("/api/v1/categories", json={"name": "Pet Supplies"})
    pets_id = uuid.UUID(created.json()["id"])
    pets = await db_session.get(Category, pets_id)
    receipt = await ReceiptFactory.create_async(user_id=user.id)
    item = await LineItemFactory.create_async(receipt=receipt, category=pets)
    rule = await CategoryRepository(db_session).save_rule(user.id, "Zoo", "Dog food", pets_id)

    async with await _as(app, db_session, user) as client:
        response = await client.delete(f"/api/v1/categories/{pets_id}?move_to_id={other.id}")

    assert response.status_code == 204
    await db_session.refresh(item)
    await db_session.refresh(rule)
    assert item.category_id == other.id
    assert rule.category_id == other.id
    assert await db_session.get(Category, pets_id) is None


@pytest.mark.asyncio
async def test_moving_items_to_uncategorized_sends_them_to_review_and_drops_the_rules(
    app: FastAPI, db_session: AsyncSession
) -> None:
    user = await UserFactory.create_async()
    uncategorized = await _built_in(db_session, UNCATEGORIZED)
    pets = await CategoryFactory.create_async(name="Pets", user_id=user.id)
    receipt = await ReceiptFactory.create_async(user_id=user.id)
    item = await LineItemFactory.create_async(receipt=receipt, category=pets)
    await CategoryRepository(db_session).save_rule(user.id, "Zoo", "Dog food", pets.id)

    async with await _as(app, db_session, user) as client:
        response = await client.delete(
            f"/api/v1/categories/{pets.id}?move_to_id={uncategorized.id}"
        )

    assert response.status_code == 204
    await db_session.refresh(item)
    assert item.category_id == uncategorized.id
    assert await CategoryRepository(db_session).list_rules(user.id) == []


@pytest.mark.asyncio
async def test_items_cannot_be_moved_into_the_category_being_deleted(
    app: FastAPI, db_session: AsyncSession
) -> None:
    """Otherwise ON DELETE SET NULL would silently strip their category."""
    user = await UserFactory.create_async()
    pets = await CategoryFactory.create_async(name="Pets", user_id=user.id)

    async with await _as(app, db_session, user) as client:
        response = await client.delete(f"/api/v1/categories/{pets.id}?move_to_id={pets.id}")

    assert response.status_code == 409
    assert await db_session.get(Category, pets.id) is not None


@pytest.mark.asyncio
async def test_deletion_is_limited_to_the_users_own_categories_and_targets(
    app: FastAPI, db_session: AsyncSession
) -> None:
    user, other = await UserFactory.create_async(), await UserFactory.create_async()
    mine = await CategoryFactory.create_async(name="Mine", user_id=user.id)
    theirs = await CategoryFactory.create_async(name="Theirs", user_id=other.id)
    groceries = await _built_in(db_session, "Groceries")

    async with await _as(app, db_session, user) as client:
        cannot_delete_theirs = await client.delete(
            f"/api/v1/categories/{theirs.id}?move_to_id={groceries.id}"
        )
        cannot_delete_built_in = await client.delete(
            f"/api/v1/categories/{groceries.id}?move_to_id={mine.id}"
        )
        cannot_move_into_theirs = await client.delete(
            f"/api/v1/categories/{mine.id}?move_to_id={theirs.id}"
        )

    assert cannot_delete_theirs.status_code == 404
    assert cannot_delete_built_in.status_code == 404
    assert cannot_move_into_theirs.status_code == 404
    assert await db_session.get(Category, mine.id) is not None
