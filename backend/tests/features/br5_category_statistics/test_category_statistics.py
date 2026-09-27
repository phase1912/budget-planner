"""Runs BR-5's Gherkin scenarios (F0.6.2).

E7 is under way: F7.1 delivers the ranked category breakdown (E1, E4), run here
against `StatisticsService` with an in-memory repository; the SQL behind it is
proven in tests/api/test_category_statistics.py. The other scenarios assert
something a later feature owns, so each stays skipped until then, as named in
`AWAITING`.
"""

import asyncio
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from pytest import FixtureRequest
from pytest_bdd import given, scenarios, then, when

from app.domain.categories import ItemView
from app.domain.statistics import StatisticsPeriod
from app.repository.receipt import CategorySpend, ItemSpend
from app.services.statistics import CategoryStatistics, StatisticsService

scenarios("category_statistics.feature")

AWAITING = {
    "test_compare_spending_across_two_months": "period comparison: F7.3 (E3)",
    "test_request_statistics_for_a_period_with_no_data": "the no-data answer: F7.4 (E5)",
    "test_request_a_custom_date_range": "arbitrary date ranges: F7.2 (E2)",
}


@pytest.fixture(autouse=True)
def skip_until_its_feature_lands(request: FixtureRequest) -> None:
    reason = AWAITING.get(request.node.name)
    if reason is not None:
        pytest.skip(f"Awaiting {reason}")


@dataclass
class _Item:
    bought: datetime
    category: str
    total: Decimal


class _InMemoryReceipts:
    """Just enough of `ReceiptRepository` for `StatisticsService`, over counted items."""

    def __init__(self) -> None:
        self.items: list[_Item] = []
        self.ids: dict[str, uuid.UUID] = {}

    async def spend_by_category(
        self, view: ItemView, *, start_date: datetime, end_date: datetime
    ) -> list[CategorySpend]:
        totals: dict[str, list[Decimal]] = {}
        for item in self.items:
            if start_date <= item.bought <= end_date:
                totals.setdefault(item.category, []).append(item.total)
        return [
            CategorySpend(self.ids.setdefault(name, uuid.uuid4()), name, len(t), sum(t, Decimal(0)))
            for name, t in totals.items()
        ]

    async def item_spend(
        self, view: ItemView, *, start_date: datetime, end_date: datetime
    ) -> ItemSpend:
        return ItemSpend(Decimal(0), 0, Decimal(0))


@pytest.fixture
def receipts() -> _InMemoryReceipts:
    return _InMemoryReceipts()


@pytest.fixture
def outcome() -> dict[str, CategoryStatistics]:
    return {}


@given("the user has categorized receipts for July 2026")
def july_receipts(receipts: _InMemoryReceipts) -> None:
    for day, category, amount in [
        (2, "Dining", "38.00"),
        (5, "Groceries", "120.40"),
        (11, "Transport", "32.40"),
        (18, "Groceries", "84.50"),
        (26, "Dining", "45.00"),
    ]:
        receipts.items.append(_Item(datetime(2026, 7, day, tzinfo=UTC), category, Decimal(amount)))
    # June's spending must not leak into July's figures.
    receipts.items.append(_Item(datetime(2026, 6, 30, tzinfo=UTC), "Transport", Decimal("500")))


@when("the user requests category statistics for July 2026")
def request_july(receipts: _InMemoryReceipts, outcome: dict[str, CategoryStatistics]) -> None:
    service = StatisticsService(receipts)  # type: ignore[arg-type]
    july = StatisticsPeriod(date(2026, 7, 1), date(2026, 7, 31))
    outcome["july"] = asyncio.run(service.category_statistics(july))


@then(
    "the agent should return total spend, percentage share, and transaction count for each category"
)
def totals_shares_and_counts(outcome: dict[str, CategoryStatistics]) -> None:
    rows = {c.name: (c.total, c.share, c.item_count) for c in outcome["july"].categories}
    assert rows == {
        "Groceries": (Decimal("204.90"), Decimal("64.0"), 2),
        "Dining": (Decimal("83.00"), Decimal("25.9"), 2),
        "Transport": (Decimal("32.40"), Decimal("10.1"), 1),
    }


@then("categories should be ranked from highest to lowest spend")
def ranked_highest_first(outcome: dict[str, CategoryStatistics]) -> None:
    totals = [c.total for c in outcome["july"].categories]
    assert totals == sorted(totals, reverse=True)
