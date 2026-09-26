"""Runs BR-4's Gherkin scenarios (F0.6.2).

E6 is under way: F6.1 delivers the month total by transaction date (D1, D2),
F6.2 the excluded-receipts notice (D3) and F6.3 the month-to-date versus
finalised label (D4, and D5's label). Those scenarios run here against
`BudgetService` with an in-memory repository; the SQL behind it is proven in
tests/api/test_budget_router.py.

D6 (F6.4, F6.5) runs against the real database instead: what it asserts is
that the flush hook drops a stored snapshot, which no in-memory stand-in has.
The rest assert something a later feature owns, so each stays skipped until
then, as named in `AWAITING`.
"""

import asyncio
import uuid
from collections.abc import Awaitable, Callable, Iterator
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from decimal import Decimal
from typing import Any

import pytest
from pytest import FixtureRequest
from pytest_bdd import given, parsers, scenarios, then, when
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.context import current_user_id
from app.domain.budget import BudgetMonth
from app.models.line_item import LineItem
from app.models.monthly_snapshot import MonthlySnapshot
from app.models.receipt import ReceiptStatus
from app.models.user import User
from app.repository.receipt import ReceiptRepository
from app.repository.snapshot import MonthlySnapshotRepository
from app.schemas.receipt import LineItemInput, UpdateReceiptRequest
from app.services.budget import BudgetService, MonthSummary
from app.services.receipt import ReceiptService
from tests.factories.base import ModelFactory
from tests.factories.receipt import ReceiptFactory
from tests.factories.user import UserFactory

scenarios("monthly_budget_calculation.feature")

AWAITING = {
    "test_show_spend_against_a_userdefined_budget_limit": "the limit percentage: F6.6 (D7)",
}


@pytest.fixture(autouse=True)
def skip_until_its_feature_lands(request: FixtureRequest) -> None:
    reason = AWAITING.get(request.node.name)
    if reason is not None:
        pytest.skip(f"Awaiting {reason}")


@dataclass
class _Receipt:
    bought: datetime
    total: Decimal
    under_review: bool


class _InMemoryReceipts:
    """Just enough of `ReceiptRepository` for `BudgetService`, over a list of receipts."""

    def __init__(self) -> None:
        self.receipts: list[_Receipt] = []

    def _in(self, start: datetime, end: datetime, under_review: bool) -> list[_Receipt]:
        return [
            r for r in self.receipts if start <= r.bought < end and r.under_review is under_review
        ]

    async def month_total(self, start: datetime, end: datetime) -> tuple[Decimal, int]:
        counted = self._in(start, end, under_review=False)
        return sum((r.total for r in counted), Decimal(0)), len(counted)

    async def month_under_review(self, start: datetime, end: datetime) -> tuple[int, Decimal]:
        held = self._in(start, end, under_review=True)
        return len(held), sum((r.total for r in held), Decimal(0))

    async def has_any(self) -> bool:
        return bool(self.receipts)


@pytest.fixture
def receipts() -> _InMemoryReceipts:
    return _InMemoryReceipts()


@pytest.fixture
def outcome() -> dict[str, MonthSummary]:
    return {}


@pytest.fixture
def clock() -> dict[str, date]:
    """The user's today; the scenarios that care about it set it."""
    return {"today": date(2026, 9, 26)}


class _InMemorySnapshots:
    """Just enough of `MonthlySnapshotRepository` for `BudgetService`."""

    def __init__(self) -> None:
        self.saved: dict[BudgetMonth, MonthlySnapshot] = {}

    async def find(self, month: BudgetMonth) -> MonthlySnapshot | None:
        return self.saved.get(month)

    async def save(self, snapshot: MonthlySnapshot) -> MonthlySnapshot:
        return self.saved.setdefault(BudgetMonth(snapshot.year, snapshot.month), snapshot)


def _summary(receipts: _InMemoryReceipts, month: BudgetMonth, today: date) -> MonthSummary:
    service = BudgetService(receipts, _InMemorySnapshots())  # type: ignore[arg-type]
    return asyncio.run(
        service.month_summary(
            month, today, user_id=uuid.uuid4(), now=datetime.combine(today, time(12), UTC)
        )
    )


@given(
    parsers.parse(
        "the user has {valid:d} valid receipts and {flagged:d} receipts flagged "
        '"requires manual review" in July 2026'
    )
)
def july_receipts(receipts: _InMemoryReceipts, valid: int, flagged: int) -> None:
    for day in range(1, valid + 1):
        receipts.receipts.append(_Receipt(datetime(2026, 7, day, tzinfo=UTC), Decimal("10"), False))
    for day in range(1, flagged + 1):
        receipts.receipts.append(_Receipt(datetime(2026, 7, day, tzinfo=UTC), Decimal("50"), True))


@when("the agent calculates the July 2026 budget")
def calculate_july(
    receipts: _InMemoryReceipts, outcome: dict[str, MonthSummary], clock: dict[str, date]
) -> None:
    outcome["july"] = _summary(receipts, BudgetMonth(2026, 7), clock["today"])


@then(parsers.parse("the total should only include the {valid:d} valid receipts"))
def total_is_valid_only(outcome: dict[str, MonthSummary], valid: int) -> None:
    july = outcome["july"]
    assert (july.total, july.receipt_count) == (Decimal(10 * valid), valid)


@then(
    parsers.parse("the summary should note that {flagged:d} receipts were excluded pending review")
)
def exclusion_is_noted(outcome: dict[str, MonthSummary], flagged: int) -> None:
    july = outcome["july"]
    assert (july.excluded_count, july.excluded_amount) == (flagged, Decimal(50 * flagged))


@given(
    parsers.parse("the user has {count:d} fully parsed and categorized receipts dated in June 2026")
)
def june_receipts(receipts: _InMemoryReceipts, count: int) -> None:
    for day in range(1, count + 1):
        receipts.receipts.append(_Receipt(datetime(2026, 6, day, tzinfo=UTC), Decimal("12"), False))


@when("the user requests the June 2026 budget summary")
def request_june(
    receipts: _InMemoryReceipts, outcome: dict[str, MonthSummary], clock: dict[str, date]
) -> None:
    outcome["summary"] = _summary(receipts, BudgetMonth(2026, 6), clock["today"])


@then("the agent should return the sum of all line-item totals for June 2026")
def june_total(outcome: dict[str, MonthSummary], receipts: _InMemoryReceipts) -> None:
    assert outcome["summary"].total == sum((r.total for r in receipts.receipts), Decimal(0))


@then("label the summary as finalized")
def labelled_final(outcome: dict[str, MonthSummary]) -> None:
    assert outcome["summary"].progress.is_complete is True


@given("the current date is July 27, 2026")
def july_27(clock: dict[str, date]) -> None:
    clock["today"] = date(2026, 7, 27)


@given("the user has receipts dated from July 1 to July 27, 2026")
def july_so_far(receipts: _InMemoryReceipts) -> None:
    for day in range(1, 28):
        receipts.receipts.append(_Receipt(datetime(2026, 7, day, tzinfo=UTC), Decimal("10"), False))


@when("the user requests the July 2026 budget summary")
def request_july(
    receipts: _InMemoryReceipts, outcome: dict[str, MonthSummary], clock: dict[str, date]
) -> None:
    outcome["summary"] = _summary(receipts, BudgetMonth(2026, 7), clock["today"])


@then("the agent should return a month-to-date total")
def month_to_date_total(outcome: dict[str, MonthSummary]) -> None:
    summary = outcome["summary"]
    assert (summary.total, summary.progress.days_elapsed) == (Decimal("270"), 27)


@then("clearly label it as incomplete")
def labelled_incomplete(outcome: dict[str, MonthSummary]) -> None:
    assert outcome["summary"].progress.is_complete is False


JUNE = BudgetMonth(2026, 6)
AFTER_JUNE = datetime(2026, 7, 15, 12, tzinfo=UTC)


class _Database:
    """One scenario's data in the real test database, committed step by step.

    pytest-bdd steps are synchronous, so each runs its own event loop and
    connection; what the steps share is the database itself, and the owner's
    account is deleted afterwards, taking its receipts and snapshots with it.
    """

    def __init__(self, url: str) -> None:
        self.url = url
        self.state: dict[str, Any] = {}

    def run[T](self, step: Callable[[AsyncSession], Awaitable[T]]) -> T:
        async def in_a_session() -> T:
            engine = create_async_engine(self.url, poolclass=NullPool)
            try:
                async with AsyncSession(engine, expire_on_commit=False) as session:
                    ModelFactory.__async_session__ = session
                    if "user_id" in self.state:
                        current_user_id.set(self.state["user_id"])
                    result = await step(session)
                    await session.commit()
                    return result
            finally:
                ModelFactory.__async_session__ = None
                await engine.dispose()

        return asyncio.run(in_a_session())

    async def june_summary(self, session: AsyncSession) -> MonthSummary:
        service = BudgetService(ReceiptRepository(session), MonthlySnapshotRepository(session))
        return await service.month_summary(
            JUNE, AFTER_JUNE.date(), user_id=self.state["user_id"], now=AFTER_JUNE
        )

    async def june_snapshot(self, session: AsyncSession) -> MonthlySnapshot | None:
        return await MonthlySnapshotRepository(session).find(JUNE)


@pytest.fixture
def database(test_database_url: str) -> Iterator[_Database]:
    db = _Database(test_database_url)
    yield db
    if "user_id" in db.state:

        async def forget_the_owner(session: AsyncSession) -> None:
            await session.execute(delete(User).where(User.id == db.state["user_id"]))

        db.run(forget_the_owner)


@given("a finalized budget snapshot exists for June 2026")
def june_is_finalised(database: _Database) -> None:
    async def a_looked_at_june(session: AsyncSession) -> None:
        user = await UserFactory.create_async()
        database.state["user_id"] = user.id
        current_user_id.set(user.id)
        receipt = await ReceiptFactory.create_async(
            user_id=user.id,
            transaction_date=datetime(2026, 6, 10, 14, 30, tzinfo=UTC),
            total_amount=Decimal("40.00"),
            status=ReceiptStatus.PARSED,
            file_ids=[],
        )
        await session.refresh(receipt, ["line_items"])
        receipt.line_items = [
            LineItem(
                name="Coffee beans",
                quantity=Decimal(1),
                unit_price=Decimal("40.00"),
                total_price=Decimal("40.00"),
            )
        ]
        await session.flush()
        database.state["receipt_id"] = receipt.id
        await database.june_summary(session)

    database.run(a_looked_at_june)
    snapshot = database.run(database.june_snapshot)
    assert snapshot is not None and snapshot.total == Decimal("40.00")
    database.state["first_snapshot"] = snapshot


@when("the user edits the total amount of a receipt dated in June 2026")
def edit_june_receipt(database: _Database) -> None:
    async def correct_the_total(session: AsyncSession) -> None:
        repository = ReceiptRepository(session)
        receipt = await repository.get_with_items(database.state["receipt_id"])
        assert receipt is not None
        line = receipt.line_items[0]
        await ReceiptService(repository=repository).update_receipt(
            receipt.id,
            UpdateReceiptRequest(
                merchant_name=receipt.merchant_name,
                transaction_date=date(2026, 6, 10),
                total_amount=Decimal("55.00"),
                line_items=[
                    LineItemInput(
                        id=line.id,
                        name=line.name,
                        quantity=Decimal(1),
                        unit_price=Decimal("55.00"),
                        total_price=Decimal("55.00"),
                    )
                ],
            ),
        )

    database.run(correct_the_total)


@then("the agent should recalculate the June 2026 budget")
def june_recalculated(database: _Database) -> None:
    june = database.run(database.june_summary)
    assert (june.total, june.progress.is_complete) == (Decimal("55.00"), True)


@then("update the stored snapshot")
def june_snapshot_updated(database: _Database) -> None:
    async def junes(session: AsyncSession) -> list[MonthlySnapshot]:
        rows = await session.execute(
            select(MonthlySnapshot).where(
                MonthlySnapshot.user_id == database.state["user_id"],
                MonthlySnapshot.year == 2026,
                MonthlySnapshot.month == 6,
            )
        )
        return list(rows.scalars())

    [snapshot] = database.run(junes)
    first: MonthlySnapshot = database.state["first_snapshot"]
    assert snapshot.total == Decimal("55.00")
    assert snapshot.id != first.id
