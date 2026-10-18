"""Income at the API boundary (F23.10)."""

import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.domain.income import IncomeChannel, IncomeKind


class IncomeRequest(BaseModel):
    """A sum that came in, as the user enters it."""

    received_on: date
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    source: str = Field(min_length=1, max_length=80)
    kind: IncomeKind = IncomeKind.SALARY
    channel: IncomeChannel = IncomeChannel.MANUAL


class IncomeDraft(BaseModel):
    """What a document says came in, not yet saved: the user confirms or corrects it (F23.11).

    Any field the document did not show is null.
    """

    amount: Decimal | None
    received_on: date | None
    source: str | None
    kind: IncomeKind


class IncomeRead(BaseModel):
    id: uuid.UUID
    received_on: date
    amount: Decimal
    source: str
    kind: IncomeKind
    channel: IncomeChannel

    model_config = ConfigDict(from_attributes=True)


class MonthIncomeRead(BaseModel):
    """A month's income: its entries, their total, or the usual amount standing in."""

    month: str
    total: Decimal | None
    entered: bool
    usual: Decimal | None
    entries: list[IncomeRead]


class BalanceRead(BaseModel):
    """What the user has now, and how it came to be (F23.14); null fields without a start."""

    balance: Decimal | None
    since: date | None
    starting: Decimal | None
    came_in: Decimal | None
    spent: Decimal | None


class PendingIncomeRead(IncomeDraft):
    """Income read off a forwarded document, waiting to be confirmed (F23.11)."""

    id: uuid.UUID

    model_config = ConfigDict(from_attributes=True)
