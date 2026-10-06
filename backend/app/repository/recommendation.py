import uuid
from collections.abc import Sequence
from datetime import UTC, date, datetime, time

from sqlalchemy import delete, exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.recommendation import Recommendation
from app.repository.base import BaseRepository


class RecommendationRepository(BaseRepository[Recommendation]):
    """The current user's recommendations (BRD F3); another user's are never seen (N2)."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Recommendation, session)

    async def list_mine(self) -> Sequence[Recommendation]:
        """Every recommendation on the user's goals, newest first."""
        stmt = self._apply_ownership(
            select(Recommendation).order_by(Recommendation.created_at.desc(), Recommendation.id)
        )
        return (await self.session.execute(stmt)).scalars().all()

    async def replace_for_goal(
        self, goal_id: uuid.UUID, recommendations: Sequence[Recommendation]
    ) -> None:
        """Drop the goal's earlier recommendations and keep these instead."""
        stale = self._apply_ownership(
            delete(Recommendation).where(Recommendation.goal_id == goal_id)
        )
        await self.session.execute(stale)
        self.session.add_all(recommendations)
        await self.session.flush()

    async def has_advice_since(self, goal_id: uuid.UUID, since: date) -> bool:
        """Whether the goal has advice given on or after `since`, whoever asked for it."""
        stmt = self._apply_ownership(
            select(
                exists().where(
                    Recommendation.goal_id == goal_id,
                    Recommendation.created_at >= datetime.combine(since, time(), tzinfo=UTC),
                )
            )
        )
        return bool((await self.session.execute(stmt)).scalar())
