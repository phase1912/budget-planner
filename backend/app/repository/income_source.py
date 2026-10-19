"""Regular incomes of an account (F23.17)."""

import uuid
from collections.abc import Sequence
from datetime import date

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.income_source import IncomeSource
from app.repository.shared import SharedWithHousehold


class IncomeSourceRepository(SharedWithHousehold[IncomeSource]):
    """Regular incomes of the signed-in user and those their household shares (N2, F12.8)."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(IncomeSource, session)

    async def running_since(self, first_day: date) -> Sequence[IncomeSource]:
        """Every regular income not ended before `first_day`, oldest first."""
        stmt = (
            select(IncomeSource)
            .where(or_(IncomeSource.ends_on.is_(None), IncomeSource.ends_on >= first_day))
            .order_by(IncomeSource.created_at)
        )
        return (await self.session.execute(self._apply_ownership(stmt))).scalars().all()

    async def current(self) -> Sequence[IncomeSource]:
        """The regular incomes still running — what Settings lists."""
        stmt = (
            select(IncomeSource)
            .where(IncomeSource.ends_on.is_(None))
            .order_by(IncomeSource.created_at)
        )
        return (await self.session.execute(self._apply_ownership(stmt))).scalars().all()

    async def running_of(
        self, user_ids: Sequence[uuid.UUID], first_day: date
    ) -> Sequence[IncomeSource]:
        """The regular incomes the given household members wrote, running from `first_day`.

        Only to divide a shared bill by income (F12.8): amounts, never shown one by one.
        The caller passes their own household's members.
        """
        stmt = select(IncomeSource).where(
            IncomeSource.user_id.in_(user_ids),
            or_(IncomeSource.ends_on.is_(None), IncomeSource.ends_on >= first_day),
        )
        return (await self.session.execute(stmt)).scalars().all()
