"""The evidence gathered for advice on a goal, from real receipts (BRD F2, N2 — F8.3)."""

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import current_user_id
from app.domain.goal_analysis import GoalAnalysis
from app.domain.goals import FinancialKind, GoalType
from app.models.category import Category
from app.models.receipt import ReceiptStatus
from app.models.user import User
from app.repository.category import CategoryRepository
from app.repository.receipt import ReceiptRepository
from app.services.goal_analysis import GoalAnalysisService
from app.services.statistics import StatisticsService
from tests.factories.category import CategoryFactory
from tests.factories.goal import GoalFactory
from tests.factories.line_item import LineItemFactory
from tests.factories.receipt import ReceiptFactory
from tests.factories.user import UserFactory

TODAY = date(2026, 9, 29)
IN_WINDOW = date(2026, 9, 10)


async def _receipt(
    user: User,
    merchant: str | None,
    items: list[tuple[str, str, Category | None]],
    *,
    on: date = IN_WINDOW,
    status: ReceiptStatus = ReceiptStatus.PARSED,
) -> None:
    receipt = await ReceiptFactory.create_async(
        user_id=user.id,
        merchant_name=merchant,
        transaction_date=datetime(on.year, on.month, on.day, 12, tzinfo=UTC),
        status=status,
    )
    for name, price, category in items:
        await LineItemFactory.create_async(
            receipt=receipt, name=name, total_price=Decimal(price), category=category
        )


async def _analyse(session: AsyncSession, user: User, **goal: Any) -> GoalAnalysis:
    current_user_id.set(user.id)
    receipts = ReceiptRepository(session)
    service = GoalAnalysisService(
        StatisticsService(receipts), receipts, CategoryRepository(session)
    )
    return await service.analyse(await GoalFactory.create_async(user_id=user.id, **goal), TODAY)


def _lifestyle(keywords: list[str], categories: list[uuid.UUID] | None = None) -> dict[str, Any]:
    return {
        "type": GoalType.LIFESTYLE,
        "financial_kind": None,
        "target_amount": None,
        "mapped_item_names": keywords,
        "mapped_category_ids": categories or [],
    }


@pytest.mark.asyncio
async def test_a_watched_keyword_finds_the_products_whose_names_contain_it(
    db_session: AsyncSession,
) -> None:
    """A goal watches "chocolate"; receipts say "Milka Chocolate 100g", however cased."""
    user = await UserFactory.create_async()
    await _receipt(user, "Fresh Market", [("Milka Chocolate 100g", "5.00", None)])
    await _receipt(user, "Fresh Market", [(" milka chocolate 100g", "5.00", None)])
    await _receipt(user, "Fresh Market", [("Bread", "4.00", None)])

    analysis = await _analyse(db_session, user, **_lifestyle(["chocolate"]))

    [item] = analysis.recurring_items
    assert (item.receipt_count, item.total) == (2, Decimal("10.00"))
    assert (item.merchant, item.merchant_receipts, item.merchant_receipt_total) == (
        "Fresh Market",
        2,
        3,
    )


@pytest.mark.asyncio
async def test_a_purchase_counts_receipts_not_lines_and_one_receipt_is_not_recurring(
    db_session: AsyncSession,
) -> None:
    user = await UserFactory.create_async()
    await _receipt(user, "Kiosk", [("Cola 0.5", "4.00", None), ("Cola 0.5", "4.00", None)])
    await _receipt(user, "Kiosk", [("Cola 0.5", "4.00", None)])
    await _receipt(user, "Kiosk", [("Cola Zero", "4.00", None), ("Cola Zero", "4.00", None)])

    analysis = await _analyse(db_session, user, **_lifestyle(["cola"]))

    assert [(i.name, i.receipt_count) for i in analysis.recurring_items] == [("Cola 0.5", 2)]


@pytest.mark.asyncio
async def test_only_parsed_receipts_within_the_window_count(db_session: AsyncSession) -> None:
    """Held-out receipts never count (D1, D3), nor does history older than the window."""
    user = await UserFactory.create_async()
    await _receipt(user, "Kiosk", [("Crisps", "6.00", None)])
    await _receipt(user, "Kiosk", [("Crisps", "6.00", None)], status=ReceiptStatus.MANUAL_REVIEW)
    await _receipt(user, "Kiosk", [("Crisps", "6.00", None)], on=date(2026, 6, 30))

    analysis = await _analyse(db_session, user, **_lifestyle(["crisps"]))

    assert analysis.recurring_items == []


@pytest.mark.asyncio
async def test_a_category_reduction_looks_only_at_its_category(db_session: AsyncSession) -> None:
    user = await UserFactory.create_async()
    dining = await CategoryFactory.create_async(name="Dining", user_id=user.id)
    other = await CategoryFactory.create_async(name="Home", user_id=user.id)
    for _ in range(2):
        await _receipt(user, "Bistro", [("Lunch menu", "35.00", dining)])
        await _receipt(user, "DIY", [("Screws", "9.00", other)])

    analysis = await _analyse(
        db_session,
        user,
        type=GoalType.FINANCIAL,
        financial_kind=FinancialKind.CATEGORY_REDUCTION,
        target_amount=Decimal(50),
        category_id=dining.id,
    )

    assert analysis.goal.category_name == "Dining"
    assert [c.name for c in analysis.goal_categories] == ["Dining"]
    assert [i.name for i in analysis.recurring_items] == ["Lunch menu"]
    assert {c.name for c in analysis.highest_spend} == {"Dining", "Home"}


@pytest.mark.asyncio
async def test_a_spending_ceiling_looks_at_every_purchase(db_session: AsyncSession) -> None:
    user = await UserFactory.create_async()
    for _ in range(2):
        await _receipt(user, "Kiosk", [("Coffee", "12.00", None), ("Bagel", "7.00", None)])

    analysis = await _analyse(db_session, user)

    assert analysis.scope.whole_spend
    assert {i.name for i in analysis.recurring_items} == {"Coffee", "Bagel"}


@pytest.mark.asyncio
async def test_a_lifestyle_goal_watching_nothing_cites_no_purchases(
    db_session: AsyncSession,
) -> None:
    user = await UserFactory.create_async()
    for _ in range(2):
        await _receipt(user, "Kiosk", [("Coffee", "12.00", None)])

    analysis = await _analyse(db_session, user, **_lifestyle([]))

    assert (analysis.recurring_items, analysis.goal_categories) == ([], [])


@pytest.mark.asyncio
async def test_the_largest_increases_compare_the_window_with_the_one_before(
    db_session: AsyncSession,
) -> None:
    user = await UserFactory.create_async()
    dining = await CategoryFactory.create_async(name="Dining", user_id=user.id)
    await _receipt(user, "Bistro", [("Dinner", "100.00", dining)], on=date(2026, 5, 10))
    await _receipt(user, "Bistro", [("Dinner", "400.00", dining)])

    analysis = await _analyse(db_session, user)

    [grown] = analysis.largest_increases
    assert (grown.standing.name, grown.change) == ("Dining", Decimal("300.00"))
    assert analysis.receipt_count == 1


@pytest.mark.asyncio
async def test_another_users_receipts_are_never_evidence(db_session: AsyncSession) -> None:
    """BRD N2: neither their purchases nor their receipts at the same shop count."""
    user = await UserFactory.create_async()
    stranger = await UserFactory.create_async()
    for _ in range(2):
        await _receipt(user, "Fresh Market", [("Chocolate bar", "4.00", None)])
    for _ in range(3):
        await _receipt(stranger, "Fresh Market", [("Chocolate bar", "4.00", None)])

    analysis = await _analyse(db_session, user, **_lifestyle(["chocolate"]))

    [item] = analysis.recurring_items
    assert (item.receipt_count, item.merchant_receipts, item.merchant_receipt_total) == (2, 2, 2)
    assert analysis.receipt_count == 2
