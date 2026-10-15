import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Self

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from app.domain.per_diem import Meal
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
    budget: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    """What the user means to spend on a personal trip (F20.3); a business trip has none."""
    advance: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    """What the employer paid ahead for a business trip, in the account's currency (F20.5)."""
    advance_paid_on: date | None = None
    """When the advance was paid: its NBP rate converts a foreign per diem (§ 20)."""

    @model_validator(mode="after")
    def _ends_after_it_starts(self) -> Self:
        if self.end_date < self.start_date:
            raise ValueError("A trip ends on or after the day it starts")
        if self.budget is not None and self.kind is TripKind.BUSINESS:
            raise ValueError("A business trip is the employer's money: it has no budget")
        if self.advance is not None and self.kind is TripKind.PERSONAL:
            raise ValueError("Only a business trip has an advance from the employer")
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
    budget: Decimal | None = None
    budget_left: Decimal | None = None
    """What is left of the budget, negative once overspent; None without a budget (F20.3)."""
    advance: Decimal | None = None
    advance_paid_on: date | None = None
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


class DayTotal(BaseModel):
    """What one day of a trip cost, in the account's currency."""

    day: date
    total: Decimal


class CategoryTotal(BaseModel):
    """What a trip spent in one category, by its stored name, in the account's currency."""

    category: str
    total: Decimal


class CurrencyTotal(BaseModel):
    """What a trip's read receipts paid in one currency come to, as printed."""

    currency: str
    total: Decimal


class PerDiemTimesRequest(BaseModel):
    """A business trip's times for its per diem, as the user gives them (F20.4, ADR-0018).

    Times carry their offset, so hours across a clock change are counted as lived.
    `abroad_from` and `abroad_to` are the border crossings or flights out of and back into
    Poland (§ 12), both or neither; `meals` the meals provided on each day, first first.
    """

    departure: AwareDatetime
    returned: AwareDatetime
    abroad_from: AwareDatetime | None = None
    abroad_to: AwareDatetime | None = None
    meals: list[list[Meal]] = Field(default=[], max_length=366)

    @model_validator(mode="after")
    def _both_border_times_or_neither(self) -> Self:
        if (self.abroad_from is None) != (self.abroad_to is None):
            raise ValueError("Give both times abroad, or neither")
        return self


class PerDiemDayResponse(BaseModel):
    """One day of a per diem: its hours, the share they earn and why, the meals off it."""

    number: int
    hours: Decimal
    share: Decimal
    rule: str
    amount: Decimal
    meals: list[Meal]
    reduction: Decimal
    meals_rule: str | None
    due: Decimal


class PerDiemPartResponse(BaseModel):
    """The per diem for the time abroad or at home, in the currency the regulation sets."""

    abroad: bool
    country: str
    currency: str
    rate: Decimal
    days: list[PerDiemDayResponse]
    total: Decimal


class PlnRateResponse(BaseModel):
    """The rate a foreign per diem was put into złoty at, or null when none was had."""

    currency: str
    rate: Decimal | None
    effective_date: date | None
    source: str | None


class PerDiemResponse(BaseModel):
    """A business trip's per diem, itemised, with the times it was worked out from (F20.4).

    `total_pln` is null when a foreign part could not be put into złoty.
    """

    departure: datetime
    returned: datetime
    abroad_from: datetime | None
    abroad_to: datetime | None
    meals: list[list[Meal]]
    parts: list[PerDiemPartResponse]
    to_pln: list[PlnRateResponse]
    total_pln: Decimal | None
    account_currency: str = "PLN"
    total_account: Decimal | None = None
    regulation: str = "Dz.U. 2023 poz. 2190"


class SettlementResponse(BaseModel):
    """What the employer owes back for a business trip, in the account's currency (F20.5).

    `to_reimburse` = expenses + per diem - advance; negative when the employee hands some
    of the advance back, null when a claimed per diem could not be converted.
    """

    currency: str
    expenses: Decimal
    per_diem: Decimal | None
    advance: Decimal
    to_reimburse: Decimal | None


class TripDetailResponse(TripResponse):
    """A trip with its receipts, oldest first, and its spending split (F20.2).

    `by_kind` holds every kind, zero ones too, in a fixed order; `by_currency` only the
    currencies paid in, largest first.
    """

    receipts: list[TripReceiptResponse]
    asking: list[TripReceiptResponse]
    """A business trip's question: receipts dated within it, the employer's or the user's?"""
    days: list[DayTotal]
    """Every day of the trip, zero ones too, oldest first (F20.3)."""
    categories: list[CategoryTotal]
    """Where the trip's money went, the largest first (F20.3)."""
    by_kind: list[KindTotal]
    by_currency: list[CurrencyTotal]
    per_diem: PerDiemResponse | None = None
    """A business trip's per diem, once the user gave its times (F20.4)."""
    settlement: SettlementResponse | None = None
    """A business trip's sum to hand in (F20.5); null for a personal trip."""


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
