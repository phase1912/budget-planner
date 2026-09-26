"""Runs BR-4's Gherkin scenarios (F0.6.2).

E6 is under way: F6.1 delivers the month total by transaction date (D1, D2),
F6.2 the excluded-receipts notice (D3) and F6.3 the month-to-date versus
finalised label (D4, and D5's label). Those scenarios run here against
`BudgetService` with an in-memory repository; the SQL behind it is proven in
tests/api/test_budget_router.py. The rest assert something a later feature
owns, so each stays skipped until then, as named in `AWAITING`.
"""

import asyncio
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from decimal import Decimal

import pytest
from pytest import FixtureRequest
from pytest_bdd import given, parsers, scenarios, then, when

from app.domain.budget import BudgetMonth
from app.models.monthly_snapshot import MonthlySnapshot
from app.services.budget import BudgetService, MonthSummary

scenarios("monthly_budget_calculation.feature")

AWAITING = {
    "test_recalculate_budget_after_receipt_edit": "stored snapshots: F6.4 and F6.5 (D6)",
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
