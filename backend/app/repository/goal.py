from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.goal import Goal
from app.repository.base import BaseRepository


class GoalRepository(BaseRepository[Goal]):
    """The current user's goals (BRD F1); another user's read as not found (N2)."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Goal, session)

    async def list_mine(self) -> Sequence[Goal]:
        """The user's goals, newest first."""
        stmt = self._apply_ownership(select(Goal).order_by(Goal.created_at.desc(), Goal.id))
        return (await self.session.execute(stmt)).scalars().all()
