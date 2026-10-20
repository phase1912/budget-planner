"""Who may have how many receipts read, and when to refuse (F10.6)."""

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.errors import ReceiptQuotaExceededError, ServiceBusyError
from app.core.config import Settings
from app.domain.quota import ReceiptQuota, month_start, next_month_start, start_of
from app.models.user import User
from app.repository.usage import UsageRepository
from app.services.plans import PlanService


def is_admin(user: User, settings: Settings) -> bool:
    """An admin by role, or by an email the deployment lists (F10.6.2).

    Being an admin lifts limits only; it never grants access to another user's data
    (BRD N2, G8).
    """
    admins = {email.lower() for email in settings.admin_emails}
    return user.role == "admin" or user.email.lower() in admins


def is_super_admin(user: User, settings: Settings) -> bool:
    """A super admin: an email the deployment lists (F18.6.1). Only they appoint admins,
    and no one can make an account one through the service."""
    return user.email.lower() in {email.lower() for email in settings.admin_emails}


class QuotaService:
    """Monthly receipt reads per account, and a daily ceiling for the whole service."""

    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.usage = UsageRepository(session)
        self.plans = PlanService(session, settings)
        self.settings = settings

    async def quota_for(self, user: User, now: datetime) -> ReceiptQuota:
        """The account's reads this calendar month (UTC) against its plan's limit (F18.4)."""
        today = now.date()
        since = start_of(month_start(today))
        used = await self.usage.receipts_read_since(since, user_id=user.id) + self._as_reads(
            await self.usage.messages_sent_since(since, user_id=user.id)
        )
        plan, terms, ends_on = await self.plans.plan_of(user, now)
        limit = None if is_admin(user, self.settings) else terms.monthly_receipts
        return ReceiptQuota(
            limit=limit,
            used=used,
            resets_on=next_month_start(today),
            plan=plan.value,
            plan_ends_on=ends_on,
            ad_free=terms.ad_free or is_admin(user, self.settings),
        )

    def _as_reads(self, messages: int) -> int:
        """Messages to the assistant in reads: every started batch of them is one (F21.1)."""
        per = self.settings.assistant_messages_per_read
        return -(-messages // per)

    async def ensure_can_talk(self, user: User, now: datetime) -> None:
        """Refuse a message to the assistant that would start a batch the quota has no read
        left for (F21.1); the rest of a started batch is already paid for."""
        sent = await self.usage.messages_sent_since(
            start_of(month_start(now.date())), user_id=user.id
        )
        needed = 1 if sent % self.settings.assistant_messages_per_read == 0 else 0
        await self.ensure_can_read(user, needed, now)

    async def ensure_can_read(self, user: User, receipts: int, now: datetime) -> None:
        """Refuse, before any model call, reads past the account's quota or the service's.

        Raises ReceiptQuotaExceededError with the limit and reset date when the account
        would go over its month, and ServiceBusyError when every non-admin account
        together has reached today's ceiling. Admins are subject to neither.
        """
        if is_admin(user, self.settings):
            return
        quota = await self.quota_for(user, now)
        if not quota.allows(receipts):
            left = quota.remaining or 0
            raise ReceiptQuotaExceededError(
                f"Your account can have {quota.limit} receipts read a month and has "
                f"{left} left; this would need {receipts}. It resets on "
                f"{quota.resets_on:%-d %B %Y}.",
                params={
                    "limit": quota.limit or 0,
                    "left": left,
                    "needed": receipts,
                    "resets_on": quota.resets_on.isoformat(),
                },
            )
        admins = await self.usage.admin_ids(self.settings.admin_emails)
        today = await self.usage.receipts_read_since(
            start_of(now.date()), excluding=admins
        ) + self._as_reads(
            await self.usage.messages_sent_since(start_of(now.date()), excluding=admins)
        )
        if today + receipts > self.settings.daily_receipt_read_ceiling:
            raise ServiceBusyError(
                "Receipt reading has reached today's limit for the whole service. "
                "Try again tomorrow."
            )
