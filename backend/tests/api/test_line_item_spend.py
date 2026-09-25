"""What a selection of line items costs on the categorisation screen (D1, D3, N2)."""

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import jwt
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.core.config import get_settings
from app.core.context import current_user_id
from app.db.session import get_db_session
from app.main import create_app
from app.models.category import Category
from app.models.line_item import LineItem
from app.models.receipt import ReceiptStatus
from app.models.user import User
from tests.factories.category import CategoryFactory
from tests.factories.receipt import ReceiptFactory
from tests.factories.user import UserFactory


async def _category(session: AsyncSession, name: str) -> Category:
    stmt = select(Category).where(Category.name == name, Category.user_id.is_(None))
    existing = (await session.execute(stmt)).scalar_one_or_none()
    return existing or await CategoryFactory.create_async(name=name, user_id=None)


async def _receipt(
    session: AsyncSession,
    owner: User,
    bought: datetime,
    lines: list[tuple[str, Category]],
    status: ReceiptStatus = ReceiptStatus.PARSED,
) -> None:
    receipt = await ReceiptFactory.create_async(
        user_id=owner.id, transaction_date=bought, status=status, file_ids=[]
    )
    await session.refresh(receipt, ["line_items"])
    receipt.line_items = [
        LineItem(
            name=f"{category.name} {amount}",
            quantity=Decimal(1),
            unit_price=Decimal(amount),
            total_price=Decimal(amount),
            category=category,
        )
        for amount, category in lines
    ]
    await session.flush()


async def _items(session: AsyncSession, user: User, **query: Any) -> dict[str, Any]:
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield session

    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db_session] = override_get_db
    token = jwt.encode(
        {"sub": str(user.id)}, get_settings().jwt_secret_key.get_secret_value(), algorithm="HS256"
    )
    current_user_id.set(user.id)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {token}"},
    ) as client:
        response = await client.get("/receipts/line-items", params={"view": "all", **query})
    assert response.status_code == 200, response.json()
    body: dict[str, Any] = response.json()
    return body


def _breakdown(body: dict[str, Any]) -> list[tuple[str, Decimal, int]]:
    return [(c["name"], Decimal(c["total_amount"]), c["item_count"]) for c in body["categories"]]


@pytest.fixture
async def shopper(db_session: AsyncSession) -> tuple[User, Category, Category]:
    """August and September of groceries and clothes, one September receipt under review."""
    user = await UserFactory.create_async()
    groceries = await _category(db_session, "Groceries")
    clothing = await CategoryFactory.create_async(name="Clothing", user_id=user.id)
    await _receipt(db_session, user, datetime(2026, 8, 20, tzinfo=UTC), [("40.00", groceries)])
    await _receipt(
        db_session,
        user,
        datetime(2026, 9, 3, tzinfo=UTC),
        [("10.00", groceries), ("60.00", clothing)],
    )
    await _receipt(
        db_session,
        user,
        datetime(2026, 9, 14, tzinfo=UTC),
        [("5.00", groceries), ("30.00", clothing)],
    )
    await _receipt(
        db_session,
        user,
        datetime(2026, 9, 20, tzinfo=UTC),
        [("999.00", clothing)],
        status=ReceiptStatus.MANUAL_REVIEW,
    )
    return user, groceries, clothing


@pytest.mark.asyncio
async def test_a_category_and_a_period_narrow_the_items_and_their_total(
    db_session: AsyncSession, shopper: tuple[User, Category, Category]
) -> None:
    user, _, clothing = shopper

    body = await _items(
        db_session,
        user,
        category_id=str(clothing.id),
        start_date="2026-09-01T00:00:00Z",
        end_date="2026-09-30T23:59:59Z",
    )

    assert {i["name"] for i in body["items"]} == {
        "Clothing 60.00",
        "Clothing 30.00",
        "Clothing 999.00",
    }
    assert Decimal(body["total_amount"]) == Decimal("90.00")


@pytest.mark.asyncio
async def test_items_under_review_are_listed_and_marked_but_held_out_of_the_total(
    db_session: AsyncSession, shopper: tuple[User, Category, Category]
) -> None:
    """The same rule as the month's budget: unreliable money is reported, not counted."""
    user, _, _ = shopper

    body = await _items(db_session, user)

    flagged = [i for i in body["items"] if i["receipt_status"] == "manual_review"]
    assert [i["name"] for i in flagged] == ["Clothing 999.00"]
    assert Decimal(body["total_amount"]) == Decimal("145.00")
    assert (body["excluded_item_count"], Decimal(body["excluded_amount"])) == (1, Decimal("999.00"))


@pytest.mark.asyncio
async def test_the_total_covers_every_page_not_just_the_one_shown(
    db_session: AsyncSession, shopper: tuple[User, Category, Category]
) -> None:
    user, _, _ = shopper

    body = await _items(db_session, user, size=2, page=1)

    assert len(body["items"]) == 2
    assert Decimal(body["total_amount"]) == Decimal("145.00")


@pytest.mark.asyncio
async def test_the_breakdown_keeps_every_category_while_one_is_picked(
    db_session: AsyncSession, shopper: tuple[User, Category, Category]
) -> None:
    """It is the list a category is picked from, so picking one must not empty it."""
    user, groceries, _ = shopper

    body = await _items(
        db_session,
        user,
        category_id=str(groceries.id),
        start_date="2026-09-01T00:00:00Z",
        end_date="2026-09-30T23:59:59Z",
    )

    assert _breakdown(body) == [
        ("Clothing", Decimal("90.00"), 2),
        ("Groceries", Decimal("15.00"), 2),
    ]


@pytest.mark.asyncio
async def test_another_users_spending_never_enters_my_totals(
    db_session: AsyncSession, shopper: tuple[User, Category, Category]
) -> None:
    """BRD N2."""
    _, groceries, _ = shopper
    me = await UserFactory.create_async()
    await _receipt(db_session, me, datetime(2026, 9, 5, tzinfo=UTC), [("7.00", groceries)])

    body = await _items(db_session, me)

    assert Decimal(body["total_amount"]) == Decimal("7.00")
    assert _breakdown(body) == [("Groceries", Decimal("7.00"), 1)]
