"""Reading and writing an account's income (F23.10)."""

from collections.abc import Sequence
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.income import Income
from app.repository.base import BaseRepository


class IncomeRepository(BaseRepository[Income]):
    """Income entries of the signed-in user only (N2)."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Income, session)

    async def between(self, start: date, end: date) -> Sequence[Income]:
        """Entries received from `start` to `end`, both included, newest first."""
        stmt = (
            select(Income)
            .where(Income.received_on >= start, Income.received_on <= end)
            .order_by(Income.received_on.desc(), Income.created_at.desc())
        )
        return (await self.session.execute(self._apply_ownership(stmt))).scalars().all()
