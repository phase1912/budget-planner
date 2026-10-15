import uuid
from datetime import date
from decimal import Decimal
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.trips import ExpenseKind, TripKind
from app.schemas.receipt import ReceiptResponse


class TripRequest(BaseModel):
    """A trip as the user records or changes it (F20.1).

    `country` is an ISO 3166-1 alpha-2 code. The end may be the start: a one-day trip.
    """

    kind: TripKind
    name: str = Field(min_length=1, max_length=120)
    country: str | None = Field(default=None, pattern=r"^[A-Za-z]{2}$")
    city: str | None = Field(default=None, max_length=120)
    start_date: date
    end_date: date
    purpose: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def _ends_after_it_starts(self) -> Self:
        if self.end_date < self.start_date:
            raise ValueError("A trip ends on or after the day it starts")
        return self


class TripResponse(BaseModel):
    """A trip with how many read receipts it holds and what they come to (F20.1)."""

    id: uuid.UUID
    kind: TripKind
    name: str
    country: str | None
    city: str | None
    start_date: date
    end_date: date
    purpose: str | None
    receipt_count: int
    total: Decimal
    asking_count: int = 0
    """Receipts dated within a business trip that nobody has said are its own yet."""

    model_config = ConfigDict(from_attributes=True)


class TripReceiptResponse(ReceiptResponse):
    """A receipt on a trip, with what it paid for and whether the user said so (F20.2)."""

    expense_kind: ExpenseKind
    expense_kind_chosen: bool


class KindTotal(BaseModel):
    """What a trip's read receipts of one kind come to, in the account's currency."""

    kind: ExpenseKind
    total: Decimal


class CurrencyTotal(BaseModel):
    """What a trip's read receipts paid in one currency come to, as printed."""

    currency: str
    total: Decimal


class TripDetailResponse(TripResponse):
    """A trip with its receipts, oldest first, and its spending split (F20.2).

    `by_kind` holds every kind, zero ones too, in a fixed order; `by_currency` only the
    currencies paid in, largest first.
    """

    receipts: list[TripReceiptResponse]
    asking: list[TripReceiptResponse]
    """A business trip's question: receipts dated within it, the employer's or the user's?"""
    by_kind: list[KindTotal]
    by_currency: list[CurrencyTotal]


class ExpenseKindRequest(BaseModel):
    """What a receipt paid for, as the user says; null gives it back to the guess."""

    kind: ExpenseKind | None


class TripSuggestionResponse(BaseModel):
    """Foreign receipts on consecutive days outside any trip: maybe an unrecorded one."""

    start: date
    end: date
    currency: str
    receipts: int
    amount: Decimal


class ReceiptTripRequest(BaseModel):
    """Where a receipt goes: into `trip_id`, out of any trip (null), or back to its dates."""

    trip_id: uuid.UUID | None = None
    automatic: bool = False
