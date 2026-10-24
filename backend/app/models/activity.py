"""What the service records about its own use (F17.3)."""

import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Model


class ActivityEvent(Model):
    """One thing a signed-in user did: who, what, when — nothing more (F17.3.1).

    Owned by the user, so the full export carries it and deleting the account removes
    it; kept 12 months (ADR-0020). Never what a receipt holds.
    """

    __tablename__ = "activity_events"
    __table_args__ = (Index("ix_activity_events_event_created_at", "event", "created_at"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event: Mapped[str] = mapped_column(String(32), nullable=False)


class PageViewCount(Model):
    """How often a public page was opened on a day, from a source (F17.3.2).

    `views` counts every opening; `entries` only the first page of a visit, which is what
    the visit's source belongs to. Counts only: no IP, no identifier, nothing that says who.
    """

    __tablename__ = "page_view_counts"
    __table_args__ = (UniqueConstraint("day", "page", "source", name="uq_page_view_counts_key"),)

    day: Mapped[date] = mapped_column(Date, nullable=False)
    page: Mapped[str] = mapped_column(String(32), nullable=False)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    views: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    entries: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class VisitPlatformCount(Model):
    """How many views and visits a day had from each platform and system (F17.3.4).

    Kept beside `PageViewCount`, not in it, so the page and source counts never change
    shape: the platform is what the visit was opened in (the website or a store app), the
    system the operating system's family from the User-Agent. Counts only, as there.
    """

    __tablename__ = "visit_platform_counts"
    __table_args__ = (
        UniqueConstraint("day", "platform", "system", name="uq_visit_platform_counts_key"),
    )

    day: Mapped[date] = mapped_column(Date, nullable=False)
    platform: Mapped[str] = mapped_column(String(16), nullable=False)
    system: Mapped[str] = mapped_column(String(16), nullable=False)
    views: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    entries: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
