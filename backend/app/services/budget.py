import uuid
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from app.domain.budget import BudgetMonth, MonthProgress, may_finalise
from app.models.monthly_snapshot import MonthlySnapshot
from app.repository.receipt import ReceiptRepository
from app.repository.snapshot import MonthlySnapshotRepository


@dataclass(frozen=True)
class MonthSummary:
    """What one month of spending adds up to (BRD D1-D5).

    `finalised_at` is when the snapshot being shown was taken, or None when the
    figure was computed live because the month is still running.
    """

    month: BudgetMonth
    total: Decimal
    receipt_count: int
    has_receipts: bool
    excluded_count: int
    excluded_amount: Decimal
    progress: MonthProgress
    finalised_at: datetime | None = None


class BudgetService:
    """Monthly budget figures for the current user (BRD BR-4)."""

    def __init__(self, receipts: ReceiptRepository, snapshots: MonthlySnapshotRepository) -> None:
        self.receipts = receipts
        self.snapshots = snapshots

    async def month_summary(
        self, month: BudgetMonth, today: date, *, user_id: uuid.UUID, now: datetime
    ) -> MonthSummary:
        """Sum the month's line items by transaction date, not upload date (D1, D2).

        A month with no receipts is 0.00, not an error: an empty month is a fact
        worth showing. `has_receipts` says whether the user has any receipts at
        all, which is what decides between the welcome screen and the month view.
        Receipts under manual review are left out of the total and counted in
        `excluded_*` instead, so the figure is never quietly incomplete (D3).
        `progress` says, as of the user's `today`, whether the month is over (D4).

        A month that is over is read from its snapshot, taken on the first look
        after it ended (D5, ADR-0010); `now` guards that against a browser clock
        running ahead, which must not freeze a month still in progress.
        """
        progress = month.progress(today)
        if not (progress.is_complete and may_finalise(month, now)):
            return await self._live(month, progress)

        snapshot = await self.snapshots.find(month)
        if snapshot is None:
            live = await self._live(month, progress)
            snapshot = await self.snapshots.save(
                MonthlySnapshot(
                    user_id=user_id,
                    year=month.year,
                    month=month.month,
                    total=live.total,
                    receipt_count=live.receipt_count,
                    excluded_count=live.excluded_count,
                    excluded_amount=live.excluded_amount,
                )
            )
        return MonthSummary(
            month=month,
            total=snapshot.total,
            receipt_count=snapshot.receipt_count,
            has_receipts=snapshot.receipt_count > 0
            or snapshot.excluded_count > 0
            or await self.receipts.has_any(),
            excluded_count=snapshot.excluded_count,
            excluded_amount=snapshot.excluded_amount,
            progress=progress,
            finalised_at=snapshot.created_at,
        )

    async def _live(self, month: BudgetMonth, progress: MonthProgress) -> MonthSummary:
        """The month computed from its receipts as they stand now."""
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
            progress=progress,
        )
