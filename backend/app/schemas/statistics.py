import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class CategoryStandingResponse(BaseModel):
    """One category's row in the ranked breakdown (BRD E1).

    `category_id` is null for items with no category at all. `share` is the
    percentage of the period's spend, to one decimal place.
    """

    category_id: uuid.UUID | None
    name: str | None
    total: Decimal
    share: Decimal
    item_count: int


class CategoryStatisticsResponse(BaseModel):
    """A period's spend by category, highest first (BRD E1, E4).

    `start` and `end` are both included. `total` and `item_count` cover the
    counted items; `excluded_*` count the items on receipts under manual review,
    left out of every figure here (D3).
    """

    start: date
    end: date
    total: Decimal
    item_count: int
    categories: list[CategoryStandingResponse]
    excluded_count: int
    excluded_amount: Decimal
