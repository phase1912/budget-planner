from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.domain.budget import BudgetMonth, MonthProgress
from app.repository.receipt import ReceiptRepository


@dataclass(frozen=True)
class MonthSummary:
    """What one month of spending adds up to (BRD D1, D2)."""

    month: BudgetMonth
    total: Decimal
    receipt_count: int
    has_receipts: bool
    excluded_count: int
    excluded_amount: Decimal
    progress: MonthProgress


class BudgetService:
    """Monthly budget figures for the current user (BRD BR-4)."""

    def __init__(self, receipts: ReceiptRepository) -> None:
        self.receipts = receipts

    async def month_summary(self, month: BudgetMonth, today: date) -> MonthSummary:
        """Sum the month's line items by transaction date, not upload date (D1, D2).

        A month with no receipts is 0.00, not an error: an empty month is a fact
        worth showing. `has_receipts` says whether the user has any receipts at
        all, which is what decides between the welcome screen and the month view.
        Receipts under manual review are left out of the total and counted in
        `excluded_*` instead, so the figure is never quietly incomplete (D3).
        `progress` says, as of the user's `today`, whether the month is over or the
        figure is month-to-date (D4).
        """
        total, count = await self.receipts.month_total(month.start, month.end)
        excluded_count, excluded_amount = await self.receipts.month_under_review(
            month.start, month.end
        )
        has_receipts = count > 0 or excluded_count > 0 or await self.receipts.has_any()
        return MonthSummary(
            month=month,
            total=total,
            receipt_count=count,
            has_receipts=has_receipts,
            excluded_count=excluded_count,
            excluded_amount=excluded_amount,
            progress=month.progress(today),
        )
