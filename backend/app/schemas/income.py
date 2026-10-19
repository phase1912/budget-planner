"""Income at the API boundary (F23.10)."""

import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.domain.income import IncomeChannel, IncomeKind


class Whose(BaseModel):
    """Whose a sum is, as the caller sees it (F12.8).

    `shared` — the household's; `mine` — the caller wrote it; `added_by` — the first name
    of the member who did, when that is someone else.
    """

    shared: bool = False
    mine: bool = True
    added_by: str | None = None


class IncomeRequest(BaseModel):
    """A sum that came in, as the user enters it."""

    received_on: date
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    source: str = Field(min_length=1, max_length=80)
    kind: IncomeKind = IncomeKind.SALARY
    channel: IncomeChannel = IncomeChannel.MANUAL
    taxed: bool | None = None
    # Shared with the household (F12.8): every member sees and changes it.
    shared: bool = False
    """Whether taxes are set aside from it (F23.16); left out, earnings are and gifts,
    refunds and sales are not — and a change leaves it as it was."""


class IncomeDraft(BaseModel):
    """What a document says came in, not yet saved: the user confirms or corrects it (F23.11).

    Any field the document did not show is null.
    """

    amount: Decimal | None
    received_on: date | None
    source: str | None
    kind: IncomeKind


class IncomeRead(Whose):
    id: uuid.UUID
    received_on: date
    amount: Decimal
    source: str
    kind: IncomeKind
    channel: IncomeChannel
    taxed: bool = False

    model_config = ConfigDict(from_attributes=True)


class MonthIncomeRead(BaseModel):
    """A month's income: its entries, their total, or the usual amount standing in."""

    month: str
    total: Decimal | None
    entered: bool
    usual: Decimal | None
    entries: list[IncomeRead]
    taxes: Decimal = Decimal("0.00")
    """Set aside for taxes this month, for a user who pays their own (F23.16)."""
    net: Decimal | None = None
    """What is left to live on: `total` less `taxes`."""
    taxes_paid: Decimal = Decimal("0.00")
    """Tax payments recorded this month."""
    regular: list["IncomeSourceRead"] = []
    """The regular incomes counted in this month (F23.17), part of `total`."""
    bills: list["RegularExpenseRead"] = []
    """The regular bills of this month (F23.18): spending without receipts."""
    bills_total: Decimal = Decimal("0.00")


class BalanceRead(BaseModel):
    """What the user has now, and how it came to be (F23.14); null fields without a start."""

    balance: Decimal | None
    since: date | None
    starting: Decimal | None
    came_in: Decimal | None
    spent: Decimal | None
    taxes_paid: Decimal | None = None
    bills: Decimal | None = None
    for_taxes: Decimal | None = None
    """Of `balance`, what is still owed in taxes (F23.16); null for most users."""


class PendingIncomeRead(IncomeDraft):
    """Income read off a forwarded document, waiting to be confirmed (F23.11)."""

    id: uuid.UUID

    model_config = ConfigDict(from_attributes=True)


class TaxPaymentRequest(BaseModel):
    """Taxes paid, by a user who pays their own (F23.16)."""

    paid_on: date
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)


class TaxPaymentRead(TaxPaymentRequest):
    id: uuid.UUID

    model_config = ConfigDict(from_attributes=True)


class IncomeSourceRequest(BaseModel):
    """A regular income, already net (F23.17); `day` is when in the month it comes.

    `shared` puts it in the household's money (F12.8): every member sees and changes it.
    """

    name: str = Field(min_length=1, max_length=80)
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    day: int | None = Field(None, ge=1, le=31)
    taxed: bool = False
    shared: bool = False


class IncomeSourceRead(IncomeSourceRequest, Whose):
    id: uuid.UUID
    starts_on: date

    model_config = ConfigDict(from_attributes=True)


class RegularExpenseRequest(BaseModel):
    """A bill paid every month without a receipt — rent, a subscription (F23.18).

    A shared one (F12.8) is the family's as a whole: it comes out of the shared budget
    once and is never divided into parts per member (ADR-0023).
    """

    name: str = Field(min_length=1, max_length=80)
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    day: int | None = Field(None, ge=1, le=31)
    shared: bool = False


class RegularExpenseRead(RegularExpenseRequest, Whose):
    id: uuid.UUID
    starts_on: date

    model_config = ConfigDict(from_attributes=True)


MonthIncomeRead.model_rebuild()
