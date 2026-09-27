import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from app.domain.budget import BudgetMonth, ReceiptOrder
from app.domain.categories import ItemView
from app.domain.periods import DateRange
from app.models.receipt import Receipt
from app.repository.receipt import CategorySpend, ReceiptRepository
from app.services.budget import BudgetService, MonthSummary

LISTED_RECEIPTS = 6
"""How many of the month's receipts the landing view lists (docs/design/screens/dashboard.html)."""


@dataclass(frozen=True)
class MonthDashboard:
    """One month as the landing view composes it: figure, categories and receipts (F6.7)."""

    summary: MonthSummary
    categories: list[CategorySpend]
    receipts: Sequence[Receipt]
    receipts_in_month: int


class DashboardService:
    """The landing view's data for one month, gathered in one call (F6.7).

    Composes three epics' figures — E6's month total, E5's spend by category and
    E3's receipts — so the page needs one round trip, and all three describe the
    same month by the same rule: a receipt belongs to the month printed on it,
    or the month it was uploaded when no date could be read (D1, D2).
    """

    def __init__(self, budget: BudgetService, receipts: ReceiptRepository) -> None:
        self.budget = budget
        self.receipts = receipts

    async def month(
        self,
        month: BudgetMonth,
        today: date,
        *,
        user_id: uuid.UUID,
        now: datetime,
        limit: Decimal | None,
    ) -> MonthDashboard:
        """The month's figure, where it went and its receipts column.

        A finished month lists its biggest receipts, a running one its newest
        (dashboard-dark.html against dashboard.html): once a month is over, what
        the money went on matters more than when. "Finished" is the user's own
        calendar, as for the finalised label (D4, ADR-0009).
        """
        summary = await self.budget.month_summary(
            month, today, user_id=user_id, now=now, limit=limit
        )
        days = DateRange.of_month(month)
        order = ReceiptOrder.LARGEST if summary.progress.is_complete else ReceiptOrder.NEWEST
        receipts, receipts_in_month = await self.receipts.list_paginated(
            0, LISTED_RECEIPTS, period=days, order=order
        )
        categories = await self.receipts.spend_by_category(ItemView.ALL, period=days)
        return MonthDashboard(summary, categories, receipts, receipts_in_month)
