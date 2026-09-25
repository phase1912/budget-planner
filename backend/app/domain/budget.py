"""The budget period: a calendar month, bounded by the dates printed on receipts.

ADR-0009 settles BRD section 14's open question in favour of calendar months,
and records why no timezone conversion happens here: a receipt's
`transaction_date` holds the shop's own wall-clock time (labelled UTC when
stored), so the month it was printed in is the month it belongs to (D2).
"""

from dataclasses import dataclass
from datetime import UTC, datetime


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
