from decimal import Decimal

from pydantic import BaseModel


class MonthSummaryResponse(BaseModel):
    """One calendar month's spend, as the month view shows it (BRD D1-D3).

    `excluded_*` count the receipts held out of `total` because they are under
    manual review, and the value of their lines.
    """

    year: int
    month: int
    total: Decimal
    receipt_count: int
    has_receipts: bool
    excluded_count: int
    excluded_amount: Decimal
