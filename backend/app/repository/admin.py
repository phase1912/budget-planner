"""Plans granted to accounts and the admin log (F18.6.3)."""

import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity import ActivityEvent
from app.models.admin import AdminAction, PlanGrant
from app.models.user import User


class AdminRepository:
    """Plan grants of an account, and the log of what admins did."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def grants_of(self, user_id: uuid.UUID) -> Sequence[PlanGrant]:
        """Every grant the account was given, newest first."""
        stmt = (
            select(PlanGrant)
            .where(PlanGrant.user_id == user_id)
            .order_by(PlanGrant.created_at.desc())
        )
        return (await self.session.execute(stmt)).scalars().all()

    async def grant(self, grant_id: uuid.UUID, user_id: uuid.UUID) -> PlanGrant | None:
        """One grant of this account's, or None."""
        stmt = select(PlanGrant).where(PlanGrant.id == grant_id, PlanGrant.user_id == user_id)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    def add(self, row: PlanGrant | AdminAction) -> None:
        self.session.add(row)

    async def log(self, limit: int, offset: int) -> Sequence[AdminAction]:
        """The admin log, newest first."""
        stmt = (
            select(AdminAction).order_by(AdminAction.created_at.desc()).limit(limit).offset(offset)
        )
        return (await self.session.execute(stmt)).scalars().all()


class AdminUsersRepository:
    """Finding accounts for the admin console: facts about them, never their receipts (N2)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def search(
        self,
        *,
        query: str,
        confirmed: bool | None,
        paid: bool | None,
        active_since: datetime | None,
        now: datetime,
        limit: int,
        offset: int,
    ) -> tuple[Sequence[User], int]:
        """Accounts matching the filters, newest first, and how many match in all."""
        stmt = select(User)
        if query:
            stmt = stmt.where(User.email.ilike(f"%{_like(query.strip())}%", escape="\\"))
        if confirmed is not None:
            stmt = stmt.where(
                User.email_confirmed_at.is_not(None)
                if confirmed
                else User.email_confirmed_at.is_(None)
            )
        if paid is not None:
            running = (
                select(PlanGrant.id)
                .where(
                    PlanGrant.user_id == User.id,
                    PlanGrant.revoked_at.is_(None),
                    PlanGrant.starts_at <= now,
                    PlanGrant.ends_at > now,
                    PlanGrant.plan != "free",
                )
                .exists()
            )
            stmt = stmt.where(running if paid else ~running)
        if active_since is not None:
            stmt = stmt.where(
                select(ActivityEvent.id)
                .where(ActivityEvent.user_id == User.id, ActivityEvent.created_at >= active_since)
                .exists()
            )
        total = int(
            await self.session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        )
        rows = await self.session.execute(
            stmt.order_by(User.created_at.desc()).limit(limit).offset(offset)
        )
        return rows.scalars().all(), total

    async def last_active(self, user_ids: Sequence[uuid.UUID]) -> dict[uuid.UUID, datetime]:
        """When each account was last seen doing anything."""
        if not user_ids:
            return {}
        stmt = (
            select(ActivityEvent.user_id, func.max(ActivityEvent.created_at))
            .where(ActivityEvent.user_id.in_(user_ids))
            .group_by(ActivityEvent.user_id)
        )
        return {row[0]: row[1] for row in (await self.session.execute(stmt)).all()}

    async def emails(self, user_ids: Sequence[uuid.UUID]) -> dict[uuid.UUID, str]:
        if not user_ids:
            return {}
        stmt = select(User.id, User.email).where(User.id.in_(user_ids))
        return {row[0]: row[1] for row in (await self.session.execute(stmt)).all()}


def _like(text: str) -> str:
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
