from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class MonthSummaryResponse(BaseModel):
    """One calendar month's spend, as the month view shows it (BRD D1-D3).

    `excluded_*` count the receipts held out of `total` because they are under
    manual review, and the value of their lines. `is_complete` false means the
    figure is month-to-date and must be labelled so (D4), with `days_elapsed` of
    `days_in_month` behind it. `finalised_at` is when a finished month's
    snapshot was taken; it is null while the month is still running (D5).
    """

    year: int
    month: int
    total: Decimal
    receipt_count: int
    has_receipts: bool
    excluded_count: int
    excluded_amount: Decimal
    is_complete: bool
    days_elapsed: int
    days_in_month: int
    finalised_at: datetime | None = None
