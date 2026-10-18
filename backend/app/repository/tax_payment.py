"""Taxes a user paid themselves (F23.16)."""

from collections.abc import Sequence
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tax_payment import TaxPayment
from app.repository.base import BaseRepository


class TaxPaymentRepository(BaseRepository[TaxPayment]):
    """Tax payments of the signed-in user only (N2)."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(TaxPayment, session)

    async def between(self, start: date, end: date) -> Sequence[TaxPayment]:
        """Payments from `start` to `end`, both included, newest first."""
        stmt = (
            select(TaxPayment)
            .where(TaxPayment.paid_on >= start, TaxPayment.paid_on <= end)
            .order_by(TaxPayment.paid_on.desc(), TaxPayment.created_at.desc())
        )
        return (await self.session.execute(self._apply_ownership(stmt))).scalars().all()

    async def total(self, start: date, end: date) -> Decimal:
        """What was paid from `start` to `end`, both included."""
        stmt = select(func.coalesce(func.sum(TaxPayment.amount), 0)).where(
            TaxPayment.paid_on >= start, TaxPayment.paid_on <= end
        )
        return Decimal((await self.session.execute(self._apply_ownership(stmt))).scalar_one())
