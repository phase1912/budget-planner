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
    whole month (D4): the screen says so. With no receipts in that period,
    `receipt_count` is 0 and `total` and `item_count` are null (E5).
    """

    start: date
    end: date
    receipt_count: int
    total: Decimal | None
    item_count: int | None
    stops_mid_month: bool


class CategoryStatisticsResponse(BaseModel):
    """A period's spend by category, highest first (BRD E1, E4).

    `start` and `end` are both included. `total` and `item_count` cover the
    counted items; `excluded_*` count the items on receipts under manual review,
    left out of every figure here (D3). `comparison` is present only when asked for;
    categories spent on only in the previous period are then listed too, at zero.

    `receipt_count` counts every receipt filed under the period, of any status.
    When it is 0 the period has no data: `total` and `item_count` are null rather
    than zeroes that would read like a real, empty spend (E5).
    """

    start: date
    end: date
    receipt_count: int
    total: Decimal | None
    item_count: int | None
    categories: list[CategoryStandingResponse]
    excluded_count: int
    excluded_amount: Decimal
    comparison: ComparisonResponse | None = None
    chart: "ChartResponse | None" = None


class BarResponse(BaseModel):
    """One bar: the spend it stands for and its height as a percentage of `scale_max`."""

    value: Decimal
    height: Decimal


class BarGroupResponse(BaseModel):
    """One category's bars side by side; `previous` is null without a comparison."""

    category_id: uuid.UUID | None
    name: str | None
    current: BarResponse
    previous: BarResponse | None


class ChartResponse(BaseModel):
    """A grouped bar chart of spend per category, ready to draw as given (BRD E6).

    `scale_max` is the round top of the value axis and `ticks` its gridlines,
    from 0 up; every bar's `height` is already a percentage of `scale_max`. The
    groups follow the ranking; `hidden` counts the categories left to the table.
    """

    scale_max: Decimal
    ticks: list[Decimal]
    groups: list[BarGroupResponse]
    hidden: int


CategoryStatisticsResponse.model_rebuild()
