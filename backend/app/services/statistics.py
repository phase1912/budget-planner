from dataclasses import dataclass
from decimal import Decimal

from app.domain.categories import ItemView
from app.domain.periods import DateRange
from app.domain.statistics import (
    CategoryChange,
    CategoryStanding,
    CategoryTotal,
    compare_categories,
    rank_categories,
)
from app.repository.receipt import ReceiptRepository


@dataclass(frozen=True)
class Comparison:
    """The period the statistics are compared against, and each category's change (E3).

    `period` is chosen like for like (`DateRange.previous`); `stops_mid_month`
    says the current period ends partway through a month, so the comparison
    stops on the same day rather than taking whole months (D4).
    """

    period: DateRange
    total: Decimal
    item_count: int
    changes: list[CategoryChange]
    stops_mid_month: bool


@dataclass(frozen=True)
class CategoryStatistics:
    """A period's spend broken down by category, ranked (BRD E1, E4).

    `total` and `item_count` cover the counted items; `excluded_*` are the items
    on receipts still under manual review, left out of every figure but named,
    so the statistics are never quietly incomplete (D3). `comparison` is present
    only when one was asked for (E3).
    """

    period: DateRange
    total: Decimal
    item_count: int
    categories: list[CategoryStanding]
    excluded_count: int
    excluded_amount: Decimal
    comparison: Comparison | None = None


class StatisticsService:
    """Category-level statistics for the current user (BRD BR-5)."""

    def __init__(self, receipts: ReceiptRepository) -> None:
        self.receipts = receipts

    async def category_statistics(
        self, period: DateRange, *, compare: bool = False
    ) -> CategoryStatistics:
        """Total spend, share and item count per category for `period`, biggest first (E1, E4).

        Counts the same items the month total does: those on parsed receipts,
        placed by their printed date or, with none, their upload date (D1-D3).
        With `compare`, the previous like-for-like period is counted the same way
        and each category's change against it is added (E3).
        """
        totals = await self._totals(period)
        held_out = await self.receipts.item_spend(ItemView.ALL, period=period)
        categories = rank_categories(totals)
        comparison = None
        if compare:
            before = period.previous()
            earlier = await self._totals(before)
            comparison = Comparison(
                period=before,
                total=sum((t.total for t in earlier), Decimal(0)),
                item_count=sum(t.item_count for t in earlier),
                changes=compare_categories(categories, earlier),
                stops_mid_month=period.stops_mid_month,
            )
        return CategoryStatistics(
            period=period,
            total=sum((c.total for c in categories), Decimal(0)),
            item_count=sum(c.item_count for c in categories),
            categories=categories,
            excluded_count=held_out.excluded_count,
            excluded_amount=held_out.excluded_amount,
            comparison=comparison,
        )

    async def _totals(self, period: DateRange) -> list[CategoryTotal]:
        spend = await self.receipts.spend_by_category(ItemView.ALL, period=period)
        return [CategoryTotal(c.category_id, c.name, c.item_count, c.total) for c in spend]
