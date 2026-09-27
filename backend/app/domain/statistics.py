"""Category statistics over a period of days (BRD BR-5).

A period is a run of whole calendar days, both ends included, read against the
dates printed on receipts: the shop's wall clock stored labelled UTC, so no
timezone conversion happens here either (ADR-0009). A receipt with no readable
date is placed by its upload date, as the month total places it (domain model).
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal

SHARE_PLACES = Decimal("0.1")
"""Shares are shown to one decimal place, as docs/design/screens/statistics.html prints them."""


@dataclass(frozen=True)
class StatisticsPeriod:
    """The days a statistics request covers, `start` to `end` inclusive (BRD E1, E2).

    Raises ValueError when `end` falls before `start`: an empty or backwards
    range is a mistake in the request, not a period with no spending.
    """

    start: date
    end: date

    def __post_init__(self) -> None:
        if self.end < self.start:
            raise ValueError(f"The period ends ({self.end}) before it starts ({self.start})")

    @property
    def first_instant(self) -> datetime:
        """Midnight at the start of `start`."""
        return datetime.combine(self.start, time(), tzinfo=UTC)

    @property
    def last_instant(self) -> datetime:
        """The last microsecond of `end`, since receipt filters include both bounds."""
        return datetime.combine(self.end + timedelta(days=1), time(), tzinfo=UTC) - timedelta(
            microseconds=1
        )


@dataclass(frozen=True)
class CategoryTotal:
    """What one category's items in a period cost, before ranking; `category_id` None is none."""

    category_id: uuid.UUID | None
    name: str | None
    item_count: int
    total: Decimal


@dataclass(frozen=True)
class CategoryStanding:
    """One category's row in the ranked breakdown (BRD E1).

    `share` is the percentage of the period's whole spend, to one decimal place;
    `item_count` is how many line items it holds, which is what a transaction is
    here, since one receipt spreads across several categories.
    """

    category_id: uuid.UUID | None
    name: str | None
    total: Decimal
    share: Decimal
    item_count: int


def rank_categories(totals: list[CategoryTotal]) -> list[CategoryStanding]:
    """Each category's total, share and item count, highest spend first (BRD E1, E4).

    Ties are broken by name so the order is stable between requests. Shares are
    of the period's whole spend; a period whose spend is zero or less (refunds
    only) gives every category a share of 0 rather than a division by zero.
    """
    overall = sum((t.total for t in totals), Decimal(0))
    ranked = sorted(totals, key=lambda t: (-t.total, t.name or ""))
    return [
        CategoryStanding(
            category_id=t.category_id,
            name=t.name,
            total=t.total,
            share=(t.total / overall * 100).quantize(SHARE_PLACES) if overall > 0 else Decimal(0),
            item_count=t.item_count,
        )
        for t in ranked
    ]
