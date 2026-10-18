"""Income waiting for the user's confirmation (F23.11)."""

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.pending_income import PendingIncome
from app.repository.base import BaseRepository


class PendingIncomeRepository(BaseRepository[PendingIncome]):
    """Pending income of the signed-in user only (N2), unless ownership is bypassed."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(PendingIncome, session)

    def bypass_ownership(self) -> "PendingIncomeRepository":
        """Skip ownership filtering, for the mail intake that has no signed-in user."""
        super().bypass_ownership()
        return self

    async def waiting(self) -> Sequence[PendingIncome]:
        """What waits to be confirmed, oldest first."""
        stmt = self._apply_ownership(select(PendingIncome).order_by(PendingIncome.created_at))
        return (await self.session.execute(stmt)).scalars().all()

    async def has_reference(self, user_id: uuid.UUID, reference: str) -> bool:
        """Whether a message already left one, so a letter delivered twice waits once."""
        stmt = select(PendingIncome.id).where(
            PendingIncome.user_id == user_id, PendingIncome.source_reference == reference
        )
        return (await self.session.execute(stmt)).first() is not None
