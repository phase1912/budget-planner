"""Own analytics at the API boundary (F17.3)."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


class PageViewRequest(BaseModel):
    """One view of a public page: which, and from where — never who (F17.3.2)."""

    page: str = Field(max_length=64)
    referrer: str | None = Field(default=None, max_length=512)
    utm_source: str | None = Field(default=None, max_length=128)
    entry: bool = False
    """The first public page of this page load: a visit, whose source is the one sent."""
    platform: Literal["web", "ios-app", "android-app"] = "web"
    """What the page was opened in: the website, or one of the store apps (F17.3.4)."""


class Count(BaseModel):
    """A name and how many."""

    name: str
    count: int


class DayFiguresRead(BaseModel):
    day: date
    visits: int
    page_views: int
    sign_ups: int
    confirmations: int
    receipts_read: int


class UsageReportRead(BaseModel):
    """The admin dashboard's figures for a period (F17.3.3): counts only, never a user.

    A visit is the first public page of a page load; `page_views` counts every opening.
    `active_week` and `active_month` are users active in the 7 and 30 days up to the
    period's end; `returning` those active in its last week and the week before. Admins
    are left out of every user figure.
    """

    start: date
    end: date
    visits: int
    page_views: int
    views_by_page: list[Count]
    visits_by_source: list[Count]
    visits_by_platform: list[Count]
    visits_by_system: list[Count]
    sign_ups: int
    confirmed: int
    with_a_receipt: int
    uploads: int
    receipts_read: int
    active_week: int
    active_month: int
    returning: int
    days: list[DayFiguresRead]
