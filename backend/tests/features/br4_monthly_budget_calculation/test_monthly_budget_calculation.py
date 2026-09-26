"""Runs BR-4's Gherkin scenarios (F0.6.2).

E6 is under way: F6.1 delivers the month total by transaction date (D1, D2)
and F6.2 the excluded-receipts notice (D3), whose scenario runs here against
`BudgetService` with an in-memory repository; the SQL behind it is proven in
tests/api/test_budget_router.py. The other scenarios also assert something a
later feature owns, so each stays skipped until then, as named in `AWAITING`.
"""

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pytest import FixtureRequest
from pytest_bdd import given, parsers, scenarios, then, when

from app.domain.budget import BudgetMonth
from app.services.budget import BudgetService, MonthSummary

scenarios("monthly_budget_calculation.feature")

AWAITING = {
    "test_calculate_completed_months_budget": "the finalised label: F6.3 and F6.4 (D5)",
    "test_calculate_inprogress_months_budget": "the month-to-date label: F6.3 (D4)",
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
def calculate_july(receipts: _InMemoryReceipts, outcome: dict[str, MonthSummary]) -> None:
    service = BudgetService(receipts)  # type: ignore[arg-type]
    outcome["july"] = asyncio.run(service.month_summary(BudgetMonth(2026, 7)))


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
