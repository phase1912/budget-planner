"""How many receipts an account may still have read this month (F10.6).

Every receipt read is a model call, so reads, not stored receipts, are what is
counted and capped. Months are calendar months in UTC, like every other month in
the product (ADR-0009).
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime, time


def month_start(day: date) -> date:
    """The first day of `day`'s month."""
    return day.replace(day=1)


def next_month_start(day: date) -> date:
    """The first day of the month after `day`'s: when a monthly quota starts afresh."""
    return date(day.year + day.month // 12, day.month % 12 + 1, 1)


def start_of(day: date) -> datetime:
    """Midnight UTC at the start of `day`."""
    return datetime.combine(day, time(), tzinfo=UTC)


@dataclass(frozen=True)
class ReceiptQuota:
    """One account's receipt reads this month against its limit.

    `limit` is None for an account without one (an admin); `resets_on` is the first
    day of next month, when `used` starts again from zero.
    """

    limit: int | None
    used: int
    resets_on: date

    @property
    def unlimited(self) -> bool:
        """Whether the account may read any number of receipts."""
        return self.limit is None

    @property
    def remaining(self) -> int | None:
        """Reads left this month, never below zero; None when unlimited."""
        return None if self.limit is None else max(self.limit - self.used, 0)

    def allows(self, receipts: int) -> bool:
        """Whether `receipts` more can be read this month."""
        return self.limit is None or self.used + receipts <= self.limit
