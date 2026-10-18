"""Regular bills of an account (F23.18)."""

from collections.abc import Sequence
from datetime import date

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.regular_expense import RegularExpense
from app.repository.base import BaseRepository


class RegularExpenseRepository(BaseRepository[RegularExpense]):
    """Regular bills of the signed-in user only (N2)."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(RegularExpense, session)

    async def running_since(self, first_day: date) -> Sequence[RegularExpense]:
        """Every regular bill not ended before `first_day`, oldest first."""
        stmt = (
            select(RegularExpense)
            .where(or_(RegularExpense.ends_on.is_(None), RegularExpense.ends_on >= first_day))
            .order_by(RegularExpense.created_at)
        )
        return (await self.session.execute(self._apply_ownership(stmt))).scalars().all()

    async def current(self) -> Sequence[RegularExpense]:
        """The regular bills still running — what Settings lists."""
        stmt = (
            select(RegularExpense)
            .where(RegularExpense.ends_on.is_(None))
            .order_by(RegularExpense.created_at)
        )
        return (await self.session.execute(self._apply_ownership(stmt))).scalars().all()
