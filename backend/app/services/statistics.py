from dataclasses import dataclass
from decimal import Decimal

from app.domain.categories import ItemView
from app.domain.statistics import (
    CategoryStanding,
    CategoryTotal,
    StatisticsPeriod,
    rank_categories,
)
from app.repository.receipt import ReceiptRepository


@dataclass(frozen=True)
class CategoryStatistics:
    """A period's spend broken down by category, ranked (BRD E1, E4).

    `total` and `item_count` cover the counted items; `excluded_*` are the items
    on receipts still under manual review, left out of every figure but named,
    so the statistics are never quietly incomplete (D3).
    """

    period: StatisticsPeriod
    total: Decimal
    item_count: int
    categories: list[CategoryStanding]
    excluded_count: int
    excluded_amount: Decimal


class StatisticsService:
    """Category-level statistics for the current user (BRD BR-5)."""

    def __init__(self, receipts: ReceiptRepository) -> None:
        self.receipts = receipts

    async def category_statistics(self, period: StatisticsPeriod) -> CategoryStatistics:
        """Total spend, share and item count per category for `period`, biggest first (E1, E4).

        Counts the same items the month total does: those on parsed receipts,
        placed by their printed date or, with none, their upload date (D1-D3).
        """
        start, end = period.first_instant, period.last_instant
        spend = await self.receipts.spend_by_category(ItemView.ALL, start_date=start, end_date=end)
        held_out = await self.receipts.item_spend(ItemView.ALL, start_date=start, end_date=end)
        categories = rank_categories(
            [CategoryTotal(c.category_id, c.name, c.item_count, c.total) for c in spend]
        )
        return CategoryStatistics(
            period=period,
            total=sum((c.total for c in categories), Decimal(0)),
            item_count=sum(c.item_count for c in categories),
            categories=categories,
            excluded_count=held_out.excluded_count,
            excluded_amount=held_out.excluded_amount,
        )
