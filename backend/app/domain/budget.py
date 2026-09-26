"""The budget period: a calendar month, bounded by the dates printed on receipts.

ADR-0009 settles BRD section 14's open question in favour of calendar months,
and records why no timezone conversion happens here: a receipt's
`transaction_date` holds the shop's own wall-clock time (labelled UTC when
stored), so the month it was printed in is the month it belongs to (D2).
"""

import calendar
import enum
import math
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal


@dataclass(frozen=True, order=True)
class BudgetMonth:
    """One calendar month, e.g. September 2026 (BRD D1, D2)."""

    year: int
    month: int

    def __post_init__(self) -> None:
        if not 1 <= self.month <= 12:
            raise ValueError(f"Month must be 1-12, not {self.month}")
        if not 1970 <= self.year <= 9999:
            raise ValueError(f"Year {self.year} is out of range")

    @property
    def start(self) -> datetime:
        """The first instant of the month; receipts on or after it may belong to it."""
        return datetime(self.year, self.month, 1, tzinfo=UTC)

    @property
    def end(self) -> datetime:
        """The first instant of the next month: an exclusive bound, so no day is lost."""
        year, month = (self.year + 1, 1) if self.month == 12 else (self.year, self.month + 1)
        return datetime(year, month, 1, tzinfo=UTC)

    @property
    def days(self) -> int:
        """How many days the month has."""
        return calendar.monthrange(self.year, self.month)[1]

    def progress(self, today: date) -> "MonthProgress":
        """How far through this month `today` is, for the month-to-date label (BRD D4).

        `today` is the user's own date, sent by their browser (ADR-0009). A month
        that has not begun yet has no days behind it and is not complete.
        """
        first, last = date(self.year, self.month, 1), date(self.year, self.month, self.days)
        if today > last:
            return MonthProgress(is_complete=True, days_elapsed=self.days, days=self.days)
        elapsed = (today - first).days + 1 if today >= first else 0
        return MonthProgress(is_complete=False, days_elapsed=elapsed, days=self.days)


EARLIEST_TIMEZONE = timedelta(hours=14)
"""UTC+14, Kiribati: the first place any calendar day begins."""


def may_finalise(month: BudgetMonth, now: datetime) -> bool:
    """Whether `month` has ended somewhere on Earth by `now`, so it may be snapshotted (D5).

    The browser says when the user's month is over (ADR-0009), but a wrong clock
    must not freeze a month that is still running. Nowhere is the time later than
    UTC+14, so a month whose end has not reached UTC+14 is over for no one.
    """
    return month.end <= now + EARLIEST_TIMEZONE


@dataclass(frozen=True)
class MonthProgress:
    """Whether a month is over, and if not, how many of its days have passed (D4).

    An incomplete month's figure is month-to-date and must say so wherever it is
    shown; a complete one is final.
    """

    is_complete: bool
    days_elapsed: int
    days: int


@dataclass(frozen=True)
class LimitUsage:
    """How a month's spend stands against the user's monthly limit (BRD D7).

    `percent` is rounded down, so a month still under its limit never reads
    100%; it does not stop at 100, because over the limit is exactly what the
    user must see. `remaining` goes negative once the limit is passed: the
    amount over it.
    """

    limit: Decimal
    percent: int
    remaining: Decimal

    @property
    def is_over(self) -> bool:
        """Whether spend has passed the limit; reaching it exactly is not over."""
        return self.remaining < 0


def limit_usage(total: Decimal, limit: Decimal | None) -> LimitUsage | None:
    """The month's spend as a share of the user's limit, or None when none is set (D7).

    The limit is presentation only (docs/design/screens/profile.html): a month,
    finished or not, is measured against the limit as it stands now, and
    changing it never rewrites a snapshot. A month made of refunds spends
    nothing of the limit rather than a negative share.
    """
    if limit is None or limit <= 0:
        return None
    percent = math.floor(max(total, Decimal(0)) / limit * 100)
    return LimitUsage(limit=limit, percent=percent, remaining=limit - total)


class ReceiptOrder(enum.StrEnum):
    """How a list of receipts is ordered (docs/design/screens/dashboard*.html).

    `newest` is the receipts screen and a running month's "Latest receipts";
    `largest` is a finished month's "Biggest receipts", where what the money
    went on matters more than when it was spent.
    """

    NEWEST = "newest"
    LARGEST = "largest"
