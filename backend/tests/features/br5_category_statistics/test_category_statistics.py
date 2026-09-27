"""Runs BR-5's Gherkin scenarios (F0.6.2).

E7 is under way: F7.1 delivers the ranked category breakdown (E1, E4), F7.2
any run of days (E2) and F7.3 the comparison of two periods (E3), run here
against `StatisticsService` with an in-memory repository; the SQL behind it is
proven in tests/api/test_category_statistics.py. The remaining scenario asserts
something a later feature owns, so it stays skipped until then, as named in
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
from app.domain.periods import DateRange
from app.repository.receipt import CategorySpend, ItemSpend
from app.services.statistics import CategoryStatistics, StatisticsService

scenarios("category_statistics.feature")

AWAITING = {
    "test_request_statistics_for_a_period_with_no_data": "the no-data answer: F7.4 (E5)",
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

    async def spend_by_category(self, view: ItemView, *, period: DateRange) -> list[CategorySpend]:
        totals: dict[str, list[Decimal]] = {}
        for item in self.items:
            if period.lower <= item.bought < period.upper:
                totals.setdefault(item.category, []).append(item.total)
        return [
            CategorySpend(self.ids.setdefault(name, uuid.uuid4()), name, len(t), sum(t, Decimal(0)))
            for name, t in totals.items()
        ]

    async def item_spend(self, view: ItemView, *, period: DateRange) -> ItemSpend:
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
    july = DateRange(date(2026, 7, 1), date(2026, 7, 31))
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


@given("the user has receipts spanning multiple months")
def several_months(receipts: _InMemoryReceipts) -> None:
    for month, day, category, amount in [
        (6, 28, "Groceries", "90.00"),
        (7, 9, "Groceries", "40.00"),
        (7, 10, "Dining", "25.00"),
        (7, 17, "Groceries", "60.00"),
        (7, 24, "Dining", "15.00"),
        (7, 25, "Groceries", "70.00"),
        (8, 3, "Dining", "80.00"),
    ]:
        receipts.items.append(
            _Item(datetime(2026, month, day, 18, tzinfo=UTC), category, Decimal(amount))
        )


@when("the user requests statistics from July 10, 2026 to July 24, 2026")
def request_mid_july(receipts: _InMemoryReceipts, outcome: dict[str, CategoryStatistics]) -> None:
    service = StatisticsService(receipts)  # type: ignore[arg-type]
    days = DateRange(date(2026, 7, 10), date(2026, 7, 24))
    outcome["range"] = asyncio.run(service.category_statistics(days))


@then("the agent should return category totals limited to that date range")
def only_those_days(outcome: dict[str, CategoryStatistics]) -> None:
    """The 10th and the 24th count; the 9th and the 25th, either side, do not."""
    rows = {c.name: c.total for c in outcome["range"].categories}
    assert rows == {"Groceries": Decimal("60.00"), "Dining": Decimal("40.00")}


@given("the user has categorized receipts for both June 2026 and July 2026")
def june_and_july(receipts: _InMemoryReceipts) -> None:
    for month, day, category, amount in [
        (6, 4, "Groceries", "812.40"),
        (6, 12, "Dining", "298.00"),
        (7, 3, "Groceries", "742.60"),
        (7, 15, "Dining", "386.00"),
    ]:
        receipts.items.append(
            _Item(datetime(2026, month, day, 12, tzinfo=UTC), category, Decimal(amount))
        )


@when("the user requests a comparison between June and July 2026")
def compare_june_july(receipts: _InMemoryReceipts, outcome: dict[str, CategoryStatistics]) -> None:
    service = StatisticsService(receipts)  # type: ignore[arg-type]
    july = DateRange(date(2026, 7, 1), date(2026, 7, 31))
    outcome["compared"] = asyncio.run(service.category_statistics(july, compare=True))


@then("the agent should return the absolute and percentage change in spend for each category")
def change_per_category(outcome: dict[str, CategoryStatistics]) -> None:
    comparison = outcome["compared"].comparison
    assert comparison is not None
    assert (comparison.period.start, comparison.period.end) == (date(2026, 6, 1), date(2026, 6, 30))
    changes = {c.standing.name: (c.change, c.change_percent) for c in comparison.changes}
    assert changes == {
        "Groceries": (Decimal("-69.80"), Decimal("-8.6")),
        "Dining": (Decimal("88.00"), Decimal("29.5")),
    }
