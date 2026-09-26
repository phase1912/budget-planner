from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.budget import BudgetMonth
from app.models.monthly_snapshot import MonthlySnapshot
from app.repository.base import BaseRepository


class MonthlySnapshotRepository(BaseRepository[MonthlySnapshot]):
    """The current user's finalised months (BRD D5); invalidation lives in the flush hook."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(model_class=MonthlySnapshot, session=session)

    async def find(self, month: BudgetMonth) -> MonthlySnapshot | None:
        """The user's snapshot of `month`, or None if it was never taken or was invalidated."""
        stmt = self._apply_ownership(
            select(MonthlySnapshot).where(
                MonthlySnapshot.year == month.year, MonthlySnapshot.month == month.month
            )
        )
        found: MonthlySnapshot | None = (await self.session.execute(stmt)).scalar_one_or_none()
        return found

    async def save(self, snapshot: MonthlySnapshot) -> MonthlySnapshot:
        """Store a snapshot; if another request stored the same month first, keep that one.

        Two tabs opening a finished month at once must not fail on the unique month.
        """
        values = {
            column: getattr(snapshot, column)
            for column in (
                "user_id",
                "year",
                "month",
                "total",
                "receipt_count",
                "excluded_count",
                "excluded_amount",
            )
        }
        await self.session.execute(
            insert(MonthlySnapshot)
            .values(**values)
            .on_conflict_do_nothing(constraint="uq_monthly_snapshot_month")
        )
        stored = await self.find(BudgetMonth(snapshot.year, snapshot.month))
        assert stored is not None
        return stored
