"""Counting receipt reads, for quotas (F10.6)."""

import uuid
from collections.abc import Collection
from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.receipt import Receipt, ReceiptChannel
from app.models.upload_job import UploadJob
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

    async def admin_ids(self, admin_emails: Collection[str]) -> list[uuid.UUID]:
        """Accounts that are admins: by role, or by an email in `admin_emails`."""
        emails = [e.lower() for e in admin_emails]
        stmt = select(User.id).where(
            or_(User.role == "admin", func.lower(User.email).in_(emails))
            if emails
            else User.role == "admin"
        )
        return list((await self.session.execute(stmt)).scalars())
