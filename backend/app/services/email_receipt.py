"""Deciding whether an inbound message may become one of a user's receipts (F11.2)."""

import enum
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, time

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.errors import ReceiptQuotaExceededError, ServiceBusyError
from app.domain.email_intake import InboundEmail, parse_message, token_from_address
from app.models.receipt import ReceiptChannel
from app.models.user import User
from app.repository.receipt import ReceiptRepository
from app.repository.user import UserRepository
from app.services.quota import QuotaService

logger = logging.getLogger(__name__)


class Refusal(enum.StrEnum):
    """Why a message was dropped rather than read."""

    UNKNOWN_RECIPIENT = "unknown_recipient"
    UNVERIFIED_SENDER = "unverified_sender"
    DAILY_LIMIT = "daily_limit"
    OVER_QUOTA = "over_quota"


@dataclass(frozen=True)
class Accepted:
    """A message cleared for reading, and whose receipt it will be."""

    user: User
    email: InboundEmail


class InboundEmailService:
    """Gatekeeper for the public forwarding addresses (F11.2).

    An address is public by nature, so a message is read only when it was sent
    to a live address, from that user's own registered email, within the day's
    limit, and within the account's monthly receipt quota (F10.6). Everything
    else is dropped and logged, never stored.
    """

    def __init__(
        self,
        session: AsyncSession,
        *,
        domain: str,
        daily_limit: int,
        quota: QuotaService | None = None,
    ) -> None:
        self.quota = quota
        self.users = UserRepository(session)
        self.receipts = ReceiptRepository(session).bypass_ownership()
        self.domain = domain
        self.daily_limit = daily_limit

    async def screen(self, raw: bytes, recipient: str, *, now: datetime) -> Accepted | Refusal:
        """Accept the message for the user `recipient` belongs to, or say why not.

        The sender check compares From with the account email. From can be
        forged, so the address token is what really keeps strangers out; the
        check stops a leaked address being used from anywhere else (ADR-0013).
        """
        token = token_from_address(recipient, self.domain)
        user = await self.users.get_by_forwarding_token(token) if token else None
        if user is None:
            logger.info("Inbound email dropped: not a forwarding address")
            return Refusal.UNKNOWN_RECIPIENT
        email = parse_message(raw)
        if email.sender != user.email.lower():
            logger.info("Inbound email for user %s dropped: unverified sender", user.id)
            return Refusal.UNVERIFIED_SENDER
        day_start = datetime.combine(now.date(), time(), tzinfo=UTC)
        received = await self.receipts.count_from_channel_since(
            user.id, ReceiptChannel.EMAIL, day_start
        )
        if received >= self.daily_limit:
            logger.info("Inbound email for user %s dropped: daily limit reached", user.id)
            return Refusal.DAILY_LIMIT
        if self.quota is not None:
            try:
                await self.quota.ensure_can_read(user, 1, now)
            except (ReceiptQuotaExceededError, ServiceBusyError):
                logger.info("Inbound email for user %s dropped: over the receipt quota", user.id)
                return Refusal.OVER_QUOTA
        return Accepted(user=user, email=email)
