"""The demo seed (F5.8): real receipts, loaded into a demo account dated to this month."""

import json
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import verify_password
from app.domain.categories import DEFAULT_CATEGORY_ORDER
from app.models.category import Category
from app.models.line_item import LineItem
from app.models.receipt import Receipt, ReceiptStatus
from app.models.user import User
from scripts.seed_demo_data import (
    DEMO_EMAIL,
    DEMO_PASSWORD,
    FIXTURE,
    export_receipts,
    load_demo,
    months_until,
    shift_months,
)
from tests.factories.category import CategoryFactory
from tests.factories.receipt import ReceiptFactory
from tests.factories.user import UserFactory

TODAY = date(2026, 11, 15)


def _line(name: str, total: str, category: str, **extra: Any) -> dict[str, Any]:
    return {
        "name": name,
        "quantity": "1",
        "unit_price": total,
        "total_price": total,
        "category": category,
        **extra,
    }


FIXTURE_DATA: dict[str, Any] = {
    "custom_categories": ["Clothing"],
    "receipts": [
        {
            "merchant_name": "Biedronka",
            "transaction_date": "2026-08-31T12:00:00+00:00",
            "total_amount": "9.49",
            "status": "parsed",
            "line_items": [
                _line("Mleko 1L", "3.50", "Groceries", category_confidence=96),
                _line("Kinder", "5.99", "No such category"),
            ],
        },
        {
            "merchant_name": "Primark",
            "transaction_date": "2026-09-14T10:00:00+00:00",
            "total_amount": None,
            "status": "manual_review",
            "line_items": [_line("T-shirt", "25.00", "Clothing", is_category_manual=True)],
        },
    ],
}


async def _ensure_built_ins(session: AsyncSession) -> None:
    """Migration tests elsewhere can leave the seeded taxonomy empty; restore it."""
    present = set(
        (await session.execute(select(Category.name).where(Category.user_id.is_(None)))).scalars()
    )
    for name in DEFAULT_CATEGORY_ORDER:
        if name not in present:
            await CategoryFactory.create_async(name=name, user_id=None)


async def _demo(session: AsyncSession) -> User:
    return (
        await session.execute(
            select(User).where(User.email == DEMO_EMAIL).execution_options(populate_existing=True)
        )
    ).scalar_one()


async def _receipts(session: AsyncSession, user: User) -> list[Receipt]:
    stmt = (
        select(Receipt)
        .where(Receipt.user_id == user.id)
        .options(selectinload(Receipt.line_items).selectinload(LineItem.category))
        .order_by(Receipt.transaction_date)
        .execution_options(populate_existing=True)
    )
    return list((await session.execute(stmt)).scalars())


def test_shifting_by_months_keeps_the_day_or_the_last_day_of_a_shorter_month() -> None:
    assert shift_months(datetime(2026, 8, 14, tzinfo=UTC), 3) == datetime(2026, 11, 14, tzinfo=UTC)
    assert shift_months(datetime(2026, 8, 31, tzinfo=UTC), 1) == datetime(2026, 9, 30, tzinfo=UTC)
    assert shift_months(datetime(2026, 11, 30, tzinfo=UTC), 3) == datetime(2027, 2, 28, tzinfo=UTC)
    assert shift_months(datetime(2026, 1, 15, tzinfo=UTC), -1) == datetime(2025, 12, 15, tzinfo=UTC)


def test_the_newest_receipt_is_brought_into_the_current_month() -> None:
    assert months_until(datetime(2026, 9, 14, tzinfo=UTC), TODAY) == 2
    assert months_until(datetime(2026, 11, 1, tzinfo=UTC), TODAY) == 0


@pytest.mark.asyncio
async def test_the_demo_user_can_sign_in_and_has_a_budget_to_measure_against(
    db_session: AsyncSession,
) -> None:
    await _ensure_built_ins(db_session)
    await load_demo(db_session, FIXTURE_DATA, TODAY)

    user = await _demo(db_session)
    assert verify_password(DEMO_PASSWORD, user.password_hash)
    assert (user.currency, user.budget_limit) == ("PLN", Decimal("3000.00"))


@pytest.mark.asyncio
async def test_receipts_land_in_this_month_and_last_with_their_categories(
    db_session: AsyncSession,
) -> None:
    await _ensure_built_ins(db_session)
    await load_demo(db_session, FIXTURE_DATA, TODAY)

    august, september = await _receipts(db_session, await _demo(db_session))

    assert august.transaction_date is not None and september.transaction_date is not None
    assert (august.transaction_date.month, august.transaction_date.day) == (10, 31)
    assert (september.transaction_date.month, september.transaction_date.day) == (11, 14)
    assert september.status is ReceiptStatus.MANUAL_REVIEW
    milk, kinder = august.line_items
    assert (milk.category.name, milk.category_confidence) == ("Groceries", 96)
    assert kinder.category.name == "Uncategorized"
    [shirt] = september.line_items
    assert shirt.category.name == "Clothing"
    assert shirt.category.user_id == september.user_id
    assert shirt.is_category_manual is True


@pytest.mark.asyncio
async def test_seeding_twice_gives_one_demo_account_not_two(db_session: AsyncSession) -> None:
    await _ensure_built_ins(db_session)
    await load_demo(db_session, FIXTURE_DATA, TODAY)
    await load_demo(db_session, FIXTURE_DATA, TODAY)

    users = await db_session.execute(select(func.count()).where(User.email == DEMO_EMAIL))
    assert users.scalar_one() == 1
    assert len(await _receipts(db_session, await _demo(db_session))) == 2


@pytest.mark.asyncio
async def test_an_export_loads_back_as_the_same_receipts(db_session: AsyncSession) -> None:
    await _ensure_built_ins(db_session)
    owner = await UserFactory.create_async()
    pets = await CategoryFactory.create_async(name="Pet Supplies", user_id=owner.id)
    receipt = await ReceiptFactory.create_async(
        user_id=owner.id,
        merchant_name="Zoo Planet",
        transaction_date=datetime(2026, 9, 3, tzinfo=UTC),
        total_amount=Decimal("39.99"),
        status=ReceiptStatus.PARSED,
        file_ids=["photo-that-must-not-travel"],
    )
    await db_session.refresh(receipt, ["line_items"])
    receipt.line_items = [
        LineItem(
            name="Dog food",
            quantity=Decimal(1),
            unit_price=Decimal("39.99"),
            total_price=Decimal("39.99"),
            category=pets,
        )
    ]
    await db_session.flush()

    fixture = await export_receipts(db_session, owner.email)
    assert fixture["custom_categories"] == ["Pet Supplies"]
    assert "photo-that-must-not-travel" not in json.dumps(fixture)

    await load_demo(db_session, fixture, date(2026, 9, 30))
    [copy] = await _receipts(db_session, await _demo(db_session))
    assert (copy.merchant_name, copy.total_amount, copy.file_ids) == (
        "Zoo Planet",
        Decimal("39.99"),
        [],
    )
    assert [(i.name, i.category.name) for i in copy.line_items] == [("Dog food", "Pet Supplies")]


def test_the_shipped_fixture_covers_two_months_and_a_receipt_under_review() -> None:
    """E6 needs this month and last, and D3 needs a flagged receipt to exclude."""
    fixture = json.loads(FIXTURE.read_text())
    newest = max(datetime.fromisoformat(r["transaction_date"]) for r in fixture["receipts"])
    offset = months_until(newest, TODAY)
    months = {
        shift_months(datetime.fromisoformat(r["transaction_date"]), offset).strftime("%Y-%m")
        for r in fixture["receipts"]
    }

    assert {"2026-11", "2026-10"} <= months
    assert any(r["status"] == "manual_review" for r in fixture["receipts"])
