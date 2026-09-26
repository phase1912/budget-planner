"""A finished month is snapshotted and stops changing, until one of its receipts does (D5, D6)."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import current_user_id
from app.models.line_item import LineItem
from app.models.monthly_snapshot import MonthlySnapshot
from app.models.receipt import Receipt
from app.models.user import User
from app.repository.receipt import ReceiptRepository
from tests.api.test_budget_router import _month, _receipt
from tests.factories.user import UserFactory

AFTER_AUGUST = "2026-09-26"


async def _snapshots(session: AsyncSession, user: User) -> list[tuple[int, int, Decimal]]:
    rows = await session.execute(
        select(MonthlySnapshot.year, MonthlySnapshot.month, MonthlySnapshot.total)
        .where(MonthlySnapshot.user_id == user.id)
        .order_by(MonthlySnapshot.year, MonthlySnapshot.month)
    )
    return [(y, m, t) for y, m, t in rows.all()]


async def _august_seen(session: AsyncSession) -> tuple[User, Receipt]:
    """A user whose August holds one 20.00 receipt, already looked at after it ended."""
    user = await UserFactory.create_async()
    receipt = await _receipt(session, user, datetime(2026, 8, 14, tzinfo=UTC), ["20.00"])
    await _month(session, user, 2026, 8, today=AFTER_AUGUST)
    return user, receipt


@pytest.mark.asyncio
async def test_the_first_look_at_a_finished_month_finalises_it(db_session: AsyncSession) -> None:
    user = await UserFactory.create_async()
    await _receipt(db_session, user, datetime(2026, 8, 14, tzinfo=UTC), ["20.00"])

    body = (await _month(db_session, user, 2026, 8, today=AFTER_AUGUST)).json()

    assert body["is_complete"] is True
    assert body["finalised_at"] is not None
    assert await _snapshots(db_session, user) == [(2026, 8, Decimal("20.00"))]


@pytest.mark.asyncio
async def test_a_finalised_month_stops_changing(db_session: AsyncSession) -> None:
    """Changed behind the ORM's back, the figure holds: it is read from the snapshot."""
    user, receipt = await _august_seen(db_session)
    await db_session.execute(
        update(LineItem)
        .where(LineItem.receipt_id == receipt.id)
        .values(total_price=Decimal("999.00"))
        .execution_options(synchronize_session=False)
    )

    body = (await _month(db_session, user, 2026, 8, today=AFTER_AUGUST)).json()

    assert Decimal(body["total"]) == Decimal("20.00")


@pytest.mark.asyncio
async def test_a_receipt_added_to_a_finalised_month_recalculates_it(
    db_session: AsyncSession,
) -> None:
    """A photo of an old receipt, uploaded late, still lands in its own month (D2, D6)."""
    user, _ = await _august_seen(db_session)
    await _receipt(db_session, user, datetime(2026, 8, 30, tzinfo=UTC), ["5.00"])

    assert await _snapshots(db_session, user) == []
    body = (await _month(db_session, user, 2026, 8, today=AFTER_AUGUST)).json()
    assert Decimal(body["total"]) == Decimal("25.00")


@pytest.mark.asyncio
async def test_editing_a_line_in_a_finalised_month_recalculates_it(
    db_session: AsyncSession,
) -> None:
    user, receipt = await _august_seen(db_session)
    line = (
        await db_session.execute(select(LineItem).where(LineItem.receipt_id == receipt.id))
    ).scalar_one()
    line.total_price = Decimal("12.00")
    await db_session.flush()

    body = (await _month(db_session, user, 2026, 8, today=AFTER_AUGUST)).json()

    assert Decimal(body["total"]) == Decimal("12.00")


@pytest.mark.asyncio
async def test_moving_a_receipt_to_another_month_recalculates_both(
    db_session: AsyncSession,
) -> None:
    user, receipt = await _august_seen(db_session)
    await _receipt(db_session, user, datetime(2026, 7, 3, tzinfo=UTC), ["1.00"])
    await _month(db_session, user, 2026, 7, today=AFTER_AUGUST)
    assert len(await _snapshots(db_session, user)) == 2

    receipt.transaction_date = datetime(2026, 7, 20, tzinfo=UTC)
    await db_session.flush()

    assert await _snapshots(db_session, user) == []
    july = (await _month(db_session, user, 2026, 7, today=AFTER_AUGUST)).json()
    august = (await _month(db_session, user, 2026, 8, today=AFTER_AUGUST)).json()
    assert (Decimal(july["total"]), Decimal(august["total"])) == (Decimal("21.00"), Decimal("0"))


@pytest.mark.asyncio
async def test_deleting_a_receipt_from_a_finalised_month_recalculates_it(
    db_session: AsyncSession,
) -> None:
    """Through the repository the app deletes with, which closes invariant 7's gap (N3)."""
    user, receipt = await _august_seen(db_session)
    current_user_id.set(user.id)

    assert await ReceiptRepository(db_session).delete(receipt.id) is True

    assert await _snapshots(db_session, user) == []
    body = (await _month(db_session, user, 2026, 8, today=AFTER_AUGUST)).json()
    assert Decimal(body["total"]) == Decimal("0")


@pytest.mark.asyncio
async def test_another_users_receipt_cannot_be_deleted_through_the_repository(
    db_session: AsyncSession,
) -> None:
    owner, receipt = await _august_seen(db_session)
    intruder = await UserFactory.create_async()
    current_user_id.set(intruder.id)

    assert await ReceiptRepository(db_session).delete(receipt.id) is False
    assert await _snapshots(db_session, owner) == [(2026, 8, Decimal("20.00"))]


@pytest.mark.asyncio
async def test_a_month_still_running_is_never_snapshotted(db_session: AsyncSession) -> None:
    user = await UserFactory.create_async()
    await _receipt(db_session, user, datetime(2026, 9, 3, tzinfo=UTC), ["10.00"])

    body = (await _month(db_session, user, 2026, 9, today=AFTER_AUGUST)).json()

    assert (body["is_complete"], body["finalised_at"]) == (False, None)
    assert await _snapshots(db_session, user) == []


@pytest.mark.asyncio
async def test_a_browser_clock_running_ahead_cannot_freeze_the_current_month(
    db_session: AsyncSession,
) -> None:
    """The label follows the browser, but nothing is stored until the month has really ended."""
    user = await UserFactory.create_async()
    current = datetime.now(UTC)
    await _receipt(db_session, user, current, ["10.00"])

    body = (await _month(db_session, user, current.year, current.month, today="9999-12-31")).json()

    assert body["is_complete"] is True
    assert body["finalised_at"] is None
    assert await _snapshots(db_session, user) == []


@pytest.mark.asyncio
async def test_one_users_change_leaves_another_users_snapshot_alone(
    db_session: AsyncSession,
) -> None:
    """BRD N2: snapshots are per user; my late receipt is not your recalculation."""
    me, _ = await _august_seen(db_session)
    other, _ = await _august_seen(db_session)
    await _receipt(db_session, me, datetime(2026, 8, 30, tzinfo=UTC), ["5.00"])

    assert await _snapshots(db_session, other) == [(2026, 8, Decimal("20.00"))]
    count = await db_session.execute(
        select(func.count()).select_from(MonthlySnapshot).where(MonthlySnapshot.user_id == me.id)
    )
    assert count.scalar_one() == 0
