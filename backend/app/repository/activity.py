"""Reading and writing the service's own-use records (F17.3).

Counts across accounts on purpose — they feed the admin dashboard — so no ownership
filter applies; nothing here returns what a user stored, only how many.
"""

import uuid
from collections.abc import Collection, Sequence
from datetime import date, datetime
from typing import Any

from sqlalchemy import Date, cast, delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import QueryableAttribute

from app.models.activity import ActivityEvent, PageViewCount
from app.models.receipt import Receipt, ReceiptChannel
from app.models.upload_job import UploadJob
from app.models.user import User


class ActivityRepository:
    """Activity events and page view counts, and the totals the dashboard reads."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def add(self, user_id: uuid.UUID, event: str) -> None:
        """Record one event; written with the request's other changes."""
        self.session.add(ActivityEvent(user_id=user_id, event=event))

    async def prune(self, before: datetime) -> int:
        """Delete events older than `before`; how many went."""
        result = await self.session.execute(
            delete(ActivityEvent).where(ActivityEvent.created_at < before)
        )
        return int(getattr(result, "rowcount", 0) or 0)

    async def recent_for(self, user_id: uuid.UUID, limit: int = 20) -> Sequence[ActivityEvent]:
        """A user's latest events, newest first (for the admin's user card, F18.6.2)."""
        stmt = (
            select(ActivityEvent)
            .where(ActivityEvent.user_id == user_id)
            .order_by(ActivityEvent.created_at.desc())
            .limit(limit)
        )
        return (await self.session.execute(stmt)).scalars().all()

    async def count_view(self, day: date, page: str, source: str, *, entry: bool) -> None:
        """Add one view of `page` from `source` on `day`, and one visit if it was the first."""
        entries = 1 if entry else 0
        stmt = insert(PageViewCount).values(
            day=day, page=page, source=source, views=1, entries=entries
        )
        await self.session.execute(
            stmt.on_conflict_do_update(
                constraint="uq_page_view_counts_key",
                set_={
                    "views": PageViewCount.views + 1,
                    "entries": PageViewCount.entries + entries,
                },
            )
        )

    async def views_by_page(self, start: date, end: date) -> list[tuple[str, int]]:
        """Every opening of each page over the days, largest first."""
        return await self._ranked(PageViewCount.page, PageViewCount.views, start, end)

    async def visits_by_source(self, start: date, end: date) -> list[tuple[str, int]]:
        """Visits — first pages only — by where they came from, largest first."""
        return await self._ranked(PageViewCount.source, PageViewCount.entries, start, end)

    async def _ranked(
        self, by: QueryableAttribute[str], counted: QueryableAttribute[int], start: date, end: date
    ) -> list[tuple[str, int]]:
        total = func.sum(counted)
        stmt = (
            select(by, total)
            .where(PageViewCount.day.between(start, end))
            .group_by(by)
            .having(total > 0)
            .order_by(total.desc(), by)
        )
        return [(name, int(n)) for name, n in (await self.session.execute(stmt)).all()]

    async def per_day_counts(self, start: date, end: date) -> dict[date, tuple[int, int]]:
        """Visits and page views on each day."""
        stmt = (
            select(
                PageViewCount.day, func.sum(PageViewCount.entries), func.sum(PageViewCount.views)
            )
            .where(PageViewCount.day.between(start, end))
            .group_by(PageViewCount.day)
        )
        return {
            day: (int(visits), int(views))
            for day, visits, views in (await self.session.execute(stmt)).all()
        }

    async def per_day(
        self,
        column: QueryableAttribute[Any],
        start: datetime,
        end: datetime,
        excluding: Collection[uuid.UUID],
    ) -> dict[date, int]:
        """How many users had `column` (a timestamp on users) fall on each day."""
        day = cast(column, Date)
        stmt = (
            select(day, func.count())
            .where(column >= start, column < end, User.id.not_in(excluding))
            .group_by(day)
        )
        return {d: int(n) for d, n in (await self.session.execute(stmt)).all()}

    async def sign_ups_per_day(
        self, start: datetime, end: datetime, excluding: Collection[uuid.UUID]
    ) -> dict[date, int]:
        return await self.per_day(User.created_at, start, end, excluding)

    async def confirmations_per_day(
        self, start: datetime, end: datetime, excluding: Collection[uuid.UUID]
    ) -> dict[date, int]:
        return await self.per_day(User.email_confirmed_at, start, end, excluding)

    async def receipts_read_per_day(
        self, start: datetime, end: datetime, excluding: Collection[uuid.UUID]
    ) -> dict[date, int]:
        """Receipts read — each one in an upload, and each emailed one — by day (F10.6)."""
        uploads = (
            select(cast(UploadJob.created_at, Date), func.sum(UploadJob.total_items))
            .where(
                UploadJob.created_at >= start,
                UploadJob.created_at < end,
                UploadJob.user_id.not_in(excluding),
            )
            .group_by(cast(UploadJob.created_at, Date))
        )
        emails = (
            select(cast(Receipt.created_at, Date), func.count())
            .where(
                Receipt.channel == ReceiptChannel.EMAIL,
                Receipt.created_at >= start,
                Receipt.created_at < end,
                Receipt.user_id.not_in(excluding),
            )
            .group_by(cast(Receipt.created_at, Date))
        )
        days: dict[date, int] = {}
        for stmt in (uploads, emails):
            for day, n in (await self.session.execute(stmt)).all():
                days[day] = days.get(day, 0) + int(n or 0)
        return days

    async def uploads(
        self, start: datetime, end: datetime, excluding: Collection[uuid.UUID]
    ) -> int:
        """Upload jobs started, each one set of photos sent to be read."""
        stmt = select(func.count()).where(
            UploadJob.created_at >= start,
            UploadJob.created_at < end,
            UploadJob.user_id.not_in(excluding),
        )
        return int(await self.session.scalar(stmt) or 0)

    async def active_users(
        self, start: datetime, end: datetime, excluding: Collection[uuid.UUID]
    ) -> set[uuid.UUID]:
        """Users with any recorded activity in the window."""
        stmt = (
            select(ActivityEvent.user_id)
            .distinct()
            .where(
                ActivityEvent.created_at >= start,
                ActivityEvent.created_at < end,
                ActivityEvent.user_id.not_in(excluding),
            )
        )
        return set((await self.session.execute(stmt)).scalars())

    async def signed_up(
        self, start: datetime, end: datetime, excluding: Collection[uuid.UUID]
    ) -> list[uuid.UUID]:
        stmt = select(User.id).where(
            User.created_at >= start, User.created_at < end, User.id.not_in(excluding)
        )
        return list((await self.session.execute(stmt)).scalars())

    async def confirmed_among(self, user_ids: list[uuid.UUID]) -> int:
        stmt = select(func.count()).where(
            User.id.in_(user_ids), User.email_confirmed_at.is_not(None)
        )
        return int(await self.session.scalar(stmt) or 0) if user_ids else 0

    async def with_a_receipt_among(self, user_ids: list[uuid.UUID]) -> int:
        stmt = select(func.count(func.distinct(Receipt.user_id))).where(
            Receipt.user_id.in_(user_ids)
        )
        return int(await self.session.scalar(stmt) or 0) if user_ids else 0
