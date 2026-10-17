"""Which plan an account is on, and what it gives (F18.4)."""

from datetime import date, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.domain.plans import GrantedPeriod, Plan, PlanTerms, current_plan, plan_terms
from app.models.user import User
from app.repository.admin import AdminRepository


class PlanService:
    """Reads an account's plan from what admins granted it; payments add to it later (F18.3)."""

    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.admin = AdminRepository(session)
        self.settings = settings

    async def plan_of(self, user: User, now: datetime) -> tuple[Plan, PlanTerms, date | None]:
        """The plan in force, its terms, and the last day it runs (None for the free plan)."""
        grants = [
            GrantedPeriod(Plan(g.plan), g.starts_at, g.ends_at, g.revoked_at is not None)
            for g in await self.admin.grants_of(user.id)
        ]
        plan, ends_at = current_plan(grants, now)
        terms = plan_terms(
            plan,
            self.settings.monthly_receipt_quota,
            self.settings.paid_monthly_receipt_quota,
        )
        last_day = (ends_at - timedelta(microseconds=1)).date() if ends_at else None
        return plan, terms, last_day
