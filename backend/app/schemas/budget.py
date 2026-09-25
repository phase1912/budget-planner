from decimal import Decimal

from pydantic import BaseModel


class MonthSummaryResponse(BaseModel):
    """One calendar month's spend, as the month view shows it (BRD D1, D2)."""

    year: int
    month: int
    total: Decimal
    receipt_count: int
    has_receipts: bool
