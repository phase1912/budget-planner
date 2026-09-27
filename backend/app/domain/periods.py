"""A run of whole days, both ends included: the one date-range rule (BRD E2).

Every date filter in the product — the receipts list, the categorisation
screen, the month view and the statistics — is a `DateRange`, so "from 10 July
to 24 July" means the same fifteen days everywhere. Days are read against the
dates printed on receipts, the shop's wall clock stored labelled UTC, so no
timezone conversion happens here (ADR-0009).
"""

import calendar
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta

from app.domain.budget import BudgetMonth


@dataclass(frozen=True)
class DateRange:
    """The days from `start` to `end`, both included (BRD E2).

    Raises ValueError when `end` falls before `start`: a backwards range is a
    mistake in the request, not a period with no spending in it. A single day
    is a range whose `start` and `end` are the same.
    """

    start: date
    end: date

    def __post_init__(self) -> None:
        if self.end < self.start:
            raise ValueError(f"The period ends ({self.end}) before it starts ({self.start})")

    @classmethod
    def of_month(cls, month: BudgetMonth) -> "DateRange":
        """Every day of one calendar month (BRD D1)."""
        return cls(month.start.date(), month.end.date() - timedelta(days=1))

    @property
    def lower(self) -> datetime:
        """The first instant inside the range: midnight starting `start`."""
        return datetime.combine(self.start, time(), tzinfo=UTC)

    @property
    def upper(self) -> datetime:
        """The first instant after the range, excluded: midnight after `end`.

        An exclusive upper bound, rather than the last second of `end`, is what
        keeps a purchase at 23:59:59.5 inside the range and none outside it.
        """
        return datetime.combine(self.end + timedelta(days=1), time(), tzinfo=UTC)

    @property
    def days(self) -> int:
        """How many days the range holds, both ends counted."""
        return (self.end - self.start).days + 1

    @property
    def stops_mid_month(self) -> bool:
        """Whether the range runs from a 1st but stops before its last month ends.

        A running month reads like this ("1-27 July"), and so does "the last three
        months" today. Such a range is compared against the same days of the months
        before, not their whole, and the screen says so (BRD D4, E3).
        """
        return self.start.day == 1 and self.end != _last_day(self.end)

    def previous(self) -> "DateRange":
        """The period this one is compared against, like for like (BRD E3).

        A range starting on a 1st is matched by month: the same days of as many
        months before, so 1-27 July meets 1-27 June and August meets July; a
        month's last day meets the other month's last day, and a day the shorter
        month lacks falls back to its last. Any other range meets the same number
        of days immediately before it.
        """
        if self.start.day != 1:
            return DateRange(self.start - timedelta(days=self.days), self.start - timedelta(days=1))
        months = (self.end.year - self.start.year) * 12 + self.end.month - self.start.month + 1
        start = _months_before(self.start, months)
        end_month = _months_before(self.end.replace(day=1), months)
        last = _last_day(end_month)
        end = (
            last
            if self.end == _last_day(self.end)
            else last.replace(day=min(self.end.day, last.day))
        )
        return DateRange(start, end)


def _last_day(day: date) -> date:
    return day.replace(day=calendar.monthrange(day.year, day.month)[1])


def _months_before(first: date, months: int) -> date:
    """The 1st of the month `months` before the one `first` falls in."""
    index = first.year * 12 + first.month - 1 - months
    return date(index // 12, index % 12 + 1, 1)
