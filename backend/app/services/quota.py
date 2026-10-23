"""Who may spend how many AI credits, and when to refuse (F10.6, F21.9, ADR-0030)."""

from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.metering import Purpose
from app.api.errors import (
    AiConsentRequiredError,
    ProblemCode,
    ReceiptQuotaExceededError,
    ServiceBusyError,
    UploadLimitExceededError,
)
from app.core.config import Settings
from app.domain.plans import Plan
from app.domain.quota import CreditWallet, month_start, next_month_start, speech_credits, start_of
from app.models.user import User
from app.repository.usage import UsageRepository
from app.services.plans import PlanService

MEASURED_DAYS = 30
"""How far back what a receipt or a message costs is measured."""
MEASURED_ENOUGH = 20
"""Reads or messages before their measured cost replaces the configured one."""


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
    """Each account's monthly wallet of AI credits, and a daily ceiling for the service.

    Every action that asks a model checks here first, against what it usually costs;
    what it really cost is recorded by the agent (F21.9.1) and spends the wallet.
    """

    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.usage = UsageRepository(session)
        self.plans = PlanService(session, settings)
        self.settings = settings

    async def quota_for(self, user: User, now: datetime) -> CreditWallet:
        """The account's wallet this calendar month (UTC) against its plan (F18.4).

        Receipts still being read count at what a receipt costs, so a burst of uploads
        cannot spend what the month does not have.
        """
        today = now.date()
        per_receipt, per_message = await self.costs(now)
        spent = await self.usage.credits_spent_since(start_of(month_start(today)), user_id=user.id)
        reading = await self.usage.receipts_being_read(user.id)
        plan, terms, ends_on = await self.plans.plan_of(user, now)
        admin = is_admin(user, self.settings)
        return CreditWallet(
            limit=None if admin else terms.monthly_credits,
            used=spent + reading * per_receipt,
            resets_on=next_month_start(today),
            per_receipt=per_receipt,
            per_message=per_message,
            plan=plan.value,
            plan_ends_on=ends_on,
            ad_free=terms.ad_free or admin,
        )

    async def costs(self, now: datetime) -> tuple[Decimal, Decimal]:
        """What a receipt read and a message to the assistant have cost lately, across the
        service; the configured figures until enough of each were recorded at a price.

        Measured from the records alone: a receipt is its reading call with the categories
        beside it, a message the assistant's calls over the messages sent since they were
        first recorded. Reads before recording began, and a model with no price (a local
        one), would make everything look free, so they never stand in for a cost.
        """
        since = now - timedelta(days=MEASURED_DAYS)
        per_receipt = Decimal(str(self.settings.credits_per_receipt))
        per_message = Decimal(str(self.settings.credits_per_message))
        reads = await self.usage.calls_for(Purpose.RECEIPT, since)
        if reads >= MEASURED_ENOUGH:
            spent = await self.usage.credits_for([Purpose.RECEIPT, Purpose.CATEGORIES], since)
            if spent > 0:
                per_receipt = spent / reads
        first = await self.usage.first_call(Purpose.ASSISTANT)
        if first is not None:
            messages = await self.usage.messages_sent_since(max(since, first))
            spent = await self.usage.credits_for([Purpose.ASSISTANT], since)
            if messages >= MEASURED_ENOUGH and spent > 0:
                per_message = spent / messages
        return per_receipt.quantize(Decimal("0.001")), per_message.quantize(Decimal("0.001"))

    async def is_free(self, user: User, now: datetime) -> bool:
        """Whether the account is on the free plan, bounded per request (F21.9.2)."""
        if is_admin(user, self.settings):
            return False
        plan, _, _ = await self.plans.plan_of(user, now)
        return plan is Plan.FREE

    async def ensure_can_read(self, user: User, receipts: int, now: datetime) -> None:
        """Refuse, before any model call, reading `receipts` the wallet cannot pay for —
        or more at once than the free plan takes."""
        if receipts > self.settings.free_receipts_per_upload and await self.is_free(user, now):
            limit = self.settings.free_receipts_per_upload
            raise UploadLimitExceededError(
                f"On the free plan one upload can hold {limit} receipts.",
                code=ProblemCode.TOO_MANY_RECEIPTS,
                params={"max": limit},
            )
        per_receipt, _ = await self.costs(now)
        await self.ensure_can_spend(user, receipts * per_receipt, now)

    async def ensure_can_talk(self, user: User, now: datetime) -> None:
        """Refuse a message to the assistant, a goal mapped or advice asked for — each about
        a message's worth of model — that the wallet cannot pay for (F21.1, F21.9)."""
        _, per_message = await self.costs(now)
        await self.ensure_can_spend(user, per_message, now)

    async def ensure_can_speak(self, user: User, seconds: Decimal, now: datetime) -> None:
        """Refuse recognising a recording of `seconds` the wallet cannot pay for (F21.2.2)."""
        await self.ensure_can_spend(user, speech_credits(seconds), now)

    async def ensure_can_spend(self, user: User, credits: Decimal, now: datetime) -> None:
        """Refuse what would cost `credits` past the account's month or the service's day.

        Raises AiConsentRequiredError (ai_consent_required) for an account that has not
        allowed the AI to read its data, admins included; ReceiptQuotaExceededError
        (quota_exceeded) saying what is left, in receipts and messages, and when the month
        renews; ServiceBusyError when every non-admin account together has spent today's
        ceiling. Admins are subject to neither of the last two.
        """
        # Asked of everyone, admins too: it is the owner's data that would leave (F25.3.2).
        if user.ai_consent_at is None:
            raise AiConsentRequiredError(
                "Allow the AI to read your receipts and messages first; it is in Settings."
            )
        if is_admin(user, self.settings):
            return
        wallet = await self.quota_for(user, now)
        if not wallet.allows(credits):
            raise ReceiptQuotaExceededError(
                f"This month's AI credits are spent: about {wallet.receipts_left or 0} "
                f"receipts or {wallet.messages_left or 0} messages are left. They renew on "
                f"{wallet.resets_on:%-d %B %Y}.",
                params={
                    "receipts_left": wallet.receipts_left or 0,
                    "messages_left": wallet.messages_left or 0,
                    "resets_on": wallet.resets_on.isoformat(),
                },
            )
        admins = await self.usage.admin_ids(self.settings.admin_emails)
        today = await self.usage.credits_spent_since(start_of(now.date()), excluding=admins)
        if today + credits > self.settings.daily_credit_ceiling:
            raise ServiceBusyError(
                "The service has reached today's limit for reading and answering. "
                "Try again tomorrow."
            )
