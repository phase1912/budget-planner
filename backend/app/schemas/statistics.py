import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class CategoryStandingResponse(BaseModel):
    """One category's row in the ranked breakdown (BRD E1).

    `category_id` is null for items with no category at all. `share` is the
    percentage of the period's spend, to one decimal place.

    With a comparison (E3), `previous_total` is what the category cost in the
    previous period and `change` the difference; `change_percent` is that as a
    percentage of the previous total, null when the category is new there. All
    three are null without a comparison.
    """

    category_id: uuid.UUID | None
    name: str | None
    total: Decimal
    share: Decimal
    item_count: int
    previous_total: Decimal | None = None
    change: Decimal | None = None
    change_percent: Decimal | None = None


class ComparisonResponse(BaseModel):
    """The previous period the statistics are measured against (BRD E3).

    `stops_mid_month` is true when the requested period ends partway through a
    month, so the previous one stops on the same day rather than taking the
    whole month (D4): the screen says so.
    """

    start: date
    end: date
    total: Decimal
    item_count: int
    stops_mid_month: bool


class CategoryStatisticsResponse(BaseModel):
    """A period's spend by category, highest first (BRD E1, E4).

    `start` and `end` are both included. `total` and `item_count` cover the
    counted items; `excluded_*` count the items on receipts under manual review,
    left out of every figure here (D3). `comparison` is present only when asked for;
    categories spent on only in the previous period are then listed too, at zero.
    """

    start: date
    end: date
    total: Decimal
    item_count: int
    categories: list[CategoryStandingResponse]
    excluded_count: int
    excluded_amount: Decimal
    comparison: ComparisonResponse | None = None
