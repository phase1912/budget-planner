"""Counting what accounts spend on models — credits, receipt reads, messages (F10.6, F21.9)."""

import uuid
from collections.abc import Collection
from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_usage import AiUsage
from app.models.conversation import ConversationMessage
from app.models.receipt import Receipt, ReceiptChannel
from app.models.upload_job import JobStatus, UploadJob
from app.models.user import User


class UsageRepository:
    """How many receipts have been read, across accounts or for one.

    A read is a receipt in an upload job, stored or not, or a receipt that arrived by
    email: each cost a model call. Spans accounts on purpose, for the service-wide
    ceiling, so it applies no ownership filter; it returns counts only, never data.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def receipts_read_since(
        self,
        since: datetime,
        *,
        user_id: uuid.UUID | None = None,
        excluding: Collection[uuid.UUID] = (),
    ) -> int:
        """Receipts read since `since`, by one account or all but `excluding`."""
        uploads = select(func.coalesce(func.sum(UploadJob.total_items), 0)).where(
            UploadJob.created_at >= since
        )
        emails = select(func.count()).where(
            Receipt.channel == ReceiptChannel.EMAIL, Receipt.created_at >= since
        )
        if user_id is not None:
            uploads = uploads.where(UploadJob.user_id == user_id)
            emails = emails.where(Receipt.user_id == user_id)
        if excluding:
            uploads = uploads.where(UploadJob.user_id.not_in(excluding))
            emails = emails.where(Receipt.user_id.not_in(excluding))
        read = int(await self.session.scalar(uploads) or 0)
        return read + int(await self.session.scalar(emails) or 0)

    async def messages_sent_since(
        self,
        since: datetime,
        *,
        user_id: uuid.UUID | None = None,
        excluding: Collection[uuid.UUID] = (),
    ) -> int:
        """Messages sent to the assistant since `since` (F21.1): each was a model call."""
        stmt = select(func.count()).where(
            ConversationMessage.role == "user", ConversationMessage.created_at >= since
        )
        if user_id is not None:
            stmt = stmt.where(ConversationMessage.user_id == user_id)
        if excluding:
            stmt = stmt.where(ConversationMessage.user_id.not_in(excluding))
        return int(await self.session.scalar(stmt) or 0)

    async def credits_spent_since(
        self,
        since: datetime,
        *,
        user_id: uuid.UUID | None = None,
        excluding: Collection[uuid.UUID] = (),
    ) -> Decimal:
        """Credits charged since `since` (F21.9.1), to one account or all but `excluding`."""
        stmt = select(func.coalesce(func.sum(AiUsage.credits), 0)).where(
            AiUsage.charged.is_(True), AiUsage.created_at >= since
        )
        if user_id is not None:
            stmt = stmt.where(AiUsage.user_id == user_id)
        if excluding:
            stmt = stmt.where(AiUsage.user_id.not_in(excluding))
        return Decimal(await self.session.scalar(stmt) or 0)

    async def receipts_being_read(self, user_id: uuid.UUID) -> int:
        """Receipts of the account's uploads still being read: spent, not yet recorded."""
        stmt = select(
            func.coalesce(func.sum(UploadJob.total_items - UploadJob.processed_items), 0)
        ).where(
            UploadJob.user_id == user_id,
            UploadJob.status.in_([JobStatus.PENDING, JobStatus.PROCESSING]),
        )
        return int(await self.session.scalar(stmt) or 0)

    async def credits_for(self, purposes: Collection[str], since: datetime) -> Decimal:
        """Credits every call for `purposes` cost since `since`, charged or not: what such
        work costs, across the service."""
        stmt = select(func.coalesce(func.sum(AiUsage.credits), 0)).where(
            AiUsage.purpose.in_(list(purposes)), AiUsage.created_at >= since
        )
        return Decimal(await self.session.scalar(stmt) or 0)

    async def calls_for(self, purpose: str, since: datetime) -> int:
        """How many calls for `purpose` were recorded since `since`, across the service."""
        stmt = select(func.count()).where(AiUsage.purpose == purpose, AiUsage.created_at >= since)
        return int(await self.session.scalar(stmt) or 0)

    async def first_call(self, purpose: str) -> datetime | None:
        """When a call for `purpose` was first recorded: before it, nothing was."""
        first: datetime | None = await self.session.scalar(
            select(func.min(AiUsage.created_at)).where(AiUsage.purpose == purpose)
        )
        return first

    async def admin_ids(self, admin_emails: Collection[str]) -> list[uuid.UUID]:
        """Accounts that are admins: by role, or by an email in `admin_emails`."""
        emails = [e.lower() for e in admin_emails]
        stmt = select(User.id).where(
            or_(User.role == "admin", func.lower(User.email).in_(emails))
            if emails
            else User.role == "admin"
        )
        return list((await self.session.execute(stmt)).scalars())
