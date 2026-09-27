"""Category statistics over a period of days (BRD BR-5).

The period is a `DateRange` (app/domain/periods.py). A receipt with no readable
date is placed by its upload date, as the month total places it (domain model).
"""

import uuid
from dataclasses import dataclass
from decimal import Decimal

SHARE_PLACES = Decimal("0.1")
"""Shares are shown to one decimal place, as docs/design/screens/statistics.html prints them."""


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


@dataclass(frozen=True)
class CategoryChange:
    """One category across two periods (BRD E3).

    `change` is this period's total less the previous one's. `change_percent` is
    that change as a percentage of the previous total, to one decimal place, and
    None when the previous period spent nothing on the category: the category is
    new, and a percentage of zero would be a division by zero.
    """

    standing: CategoryStanding
    previous_total: Decimal
    change: Decimal
    change_percent: Decimal | None


def compare_categories(
    current: list[CategoryStanding], previous: list[CategoryTotal]
) -> list[CategoryChange]:
    """Every category of either period with its change between them (BRD E3).

    Keeps the ranking of `current` (E4). A category spent on only in the previous
    period is kept too, at zero now and down 100%, after the ranked ones and by
    what it cost then, so a spend that stopped does not silently disappear.
    """
    before = {(t.category_id, t.name): t.total for t in previous}
    rows = [_change(c, before.pop((c.category_id, c.name), Decimal(0))) for c in current]
    gone = sorted(before.items(), key=lambda kv: (-kv[1], kv[0][1] or ""))
    for (category_id, name), total in gone:
        dropped = CategoryStanding(category_id, name, Decimal(0), Decimal(0), 0)
        rows.append(_change(dropped, total))
    return rows


def _change(standing: CategoryStanding, previous_total: Decimal) -> CategoryChange:
    change = standing.total - previous_total
    percent = (change / previous_total * 100).quantize(SHARE_PLACES) if previous_total else None
    return CategoryChange(standing, previous_total, change, percent)
