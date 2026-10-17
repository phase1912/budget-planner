"""Recording the service's own use, and reading it back for admins (F17.3)."""

import uuid
from collections.abc import Collection
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import ClassVar

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.activity import ACTIVITY_RETENTION, PUBLIC_PAGES, ActivityKind
from app.domain.periods import DateRange
from app.repository.activity import ActivityRepository
from app.repository.usage import UsageRepository


class ActivityService:
    """Writes what signed-in users do and counts visits to the public pages.

    An event is added to the request's session, so it is kept only if the action it
    records succeeds. "Active" is recorded once per user per day per process: with at
    most two instances, a user may get two a day, and active users are counted distinct.
    """

    _seen_today: ClassVar[dict[uuid.UUID, date]] = {}

    def __init__(self, session: AsyncSession) -> None:
        self.activity = ActivityRepository(session)

    def record(self, user_id: uuid.UUID, kind: ActivityKind) -> None:
        """Record that `user_id` did `kind` now."""
        self.activity.add(user_id, kind.value)

    def seen(self, user_id: uuid.UUID, today: date) -> None:
        """Record the user as active today, unless already recorded by this process."""
        if self._seen_today.get(user_id) == today:
            return
        self._seen_today[user_id] = today
        self.record(user_id, ActivityKind.ACTIVE)

    async def count_view(self, page: str, source: str, today: date, *, entry: bool) -> bool:
        """Count one view of a public page, and a visit when it is the first of one (F17.3.2).

        False for a path that is not a public page: nothing is counted.
        """
        if page not in PUBLIC_PAGES:
            return False
        await self.activity.count_view(today, page, source, entry=entry)
        return True

    async def prune(self, now: datetime) -> int:
        """Delete activity older than the retention period (ADR-0020); how many went."""
        return await self.activity.prune(now - ACTIVITY_RETENTION)


@dataclass(frozen=True)
class DayFigures:
    """One day of the dashboard's chart."""

    day: date
    visits: int
    page_views: int
    sign_ups: int
    confirmations: int
    receipts_read: int


@dataclass(frozen=True)
class UsageReport:
    """What the admin dashboard shows for a period (F17.3.3); counts only, never a user."""

    period: DateRange
    visits: int
    page_views: int
    views_by_page: list[tuple[str, int]]
    visits_by_source: list[tuple[str, int]]
    sign_ups: int
    confirmed: int
    with_a_receipt: int
    uploads: int
    receipts_read: int
    active_week: int
    active_month: int
    returning: int
    days: list[DayFigures]


class UsageReportService:
    """Puts the dashboard together from the activity log and the service's own tables.

    A visit is the first public page of a page load, and its source is where it came
    from; page views count every opening. Sign-ups, confirmations and receipts come from
    the tables that hold them, so the figures reach back before activity was recorded;
    who is active and who returns comes from the activity log, measured at the period's
    end. Admins — the people testing the service — are left out of every user figure.
    """

    def __init__(self, session: AsyncSession, admin_emails: Collection[str] = ()) -> None:
        self.activity = ActivityRepository(session)
        self.usage = UsageRepository(session)
        self.admin_emails = admin_emails

    async def report(self, period: DateRange) -> UsageReport:
        """The figures for `period`, both days included."""
        start, end = period.lower, period.upper
        repo = self.activity
        admins = await self.usage.admin_ids(self.admin_emails)
        pages = await repo.per_day_counts(period.start, period.end)
        sign_ups = await repo.sign_ups_per_day(start, end, admins)
        confirmations = await repo.confirmations_per_day(start, end, admins)
        reads = await repo.receipts_read_per_day(start, end, admins)
        week = await repo.active_users(end - timedelta(days=7), end, admins)
        before = await repo.active_users(end - timedelta(days=14), end - timedelta(days=7), admins)
        joined = await repo.signed_up(start, end, admins)
        days = [
            DayFigures(
                day,
                pages.get(day, (0, 0))[0],
                pages.get(day, (0, 0))[1],
                sign_ups.get(day, 0),
                confirmations.get(day, 0),
                reads.get(day, 0),
            )
            for day in (period.start + timedelta(days=i) for i in range(period.days))
        ]
        return UsageReport(
            period=period,
            visits=sum(visits for visits, _ in pages.values()),
            page_views=sum(views for _, views in pages.values()),
            views_by_page=await repo.views_by_page(period.start, period.end),
            visits_by_source=await repo.visits_by_source(period.start, period.end),
            sign_ups=len(joined),
            confirmed=await repo.confirmed_among(joined),
            with_a_receipt=await repo.with_a_receipt_among(joined),
            uploads=await repo.uploads(start, end, admins),
            receipts_read=sum(reads.values()),
            active_week=len(week),
            active_month=len(await repo.active_users(end - timedelta(days=30), end, admins)),
            returning=len(week & before),
            days=days,
        )
