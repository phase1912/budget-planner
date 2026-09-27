"""A run of whole days, both ends included: the one date-range rule (BRD E2).

Every date filter in the product — the receipts list, the categorisation
screen, the month view and the statistics — is a `DateRange`, so "from 10 July
to 24 July" means the same fifteen days everywhere. Days are read against the
dates printed on receipts, the shop's wall clock stored labelled UTC, so no
timezone conversion happens here (ADR-0009).
"""

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
