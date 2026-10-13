from datetime import date

from pydantic import BaseModel


class ShopAccuracyResponse(BaseModel):
    """One shop behind corrections: its receipts and how many needed correcting."""

    merchant: str
    receipts: int
    corrected: int


class MonthAccuracyResponse(BaseModel):
    """One month's receipts, by the day they were read, and how many needed correcting."""

    month: date
    receipts: int
    corrected: int


class ReadingAccuracyResponse(BaseModel):
    """How often reading needed the user's correction, by shop and over time (F15.4).

    `remembered_lines` are lines a remembered correction fixed by itself (F15.3), counted
    apart from the ones the user had to change.
    """

    receipts: int
    corrected_receipts: int
    lines: int
    corrected_lines: int
    remembered_lines: int
    shops: list[ShopAccuracyResponse]
    months: list[MonthAccuracyResponse]
