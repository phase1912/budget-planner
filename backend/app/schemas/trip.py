import uuid
from datetime import date
from decimal import Decimal
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.trips import TripKind
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

    model_config = ConfigDict(from_attributes=True)


class TripDetailResponse(TripResponse):
    """A trip with its receipts, oldest first."""

    receipts: list[ReceiptResponse]


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
