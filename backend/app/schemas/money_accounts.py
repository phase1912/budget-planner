"""Accounts at the API boundary (F23.15)."""

import uuid
from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.domain.accounts import AccountKind, EntryKind
from app.schemas.income import Whose


class AccountRequest(BaseModel):
    """An account as the user opens or changes it.

    `opening` is what was on it on `opening_on`; `tax_rate` is kept on a business
    account only; `shared` puts it in the household's money (F12.8).
    """

    name: str = Field(min_length=1, max_length=60)
    kind: AccountKind = AccountKind.PERSONAL
    opening: Decimal = Field(max_digits=12, decimal_places=2)
    opening_on: date | None = None
    tax_rate: Decimal | None = Field(None, ge=0, le=100, max_digits=5, decimal_places=2)
    shared: bool = False
    for_purchases: bool = False


class AccountRead(Whose):
    """An account and what is on it now."""

    id: uuid.UUID
    name: str
    kind: AccountKind
    opening: Decimal
    opening_on: date
    tax_rate: Decimal | None
    for_purchases: bool
    balance: Decimal
    set_aside: Decimal
    """Of `balance`, what is still owed in taxes on a business account."""

    model_config = ConfigDict(from_attributes=True)


class AccountsRead(BaseModel):
    """Every account the caller sees, and the money on them together."""

    accounts: list[AccountRead]
    total: Decimal
    set_aside: Decimal


class EntryRead(BaseModel):
    """One line of an account's history.

    `ref` and `ref_id` say what to change it through ("income", "move", "bill", "rule",
    "source"), null for a day's purchases; `editable` is false in a closed month.
    """

    day: date
    kind: EntryKind
    name: str
    amount: Decimal
    tax: Decimal
    by_rule: bool
    upcoming: bool
    count: int
    author: str | None
    ref: str | None
    ref_id: uuid.UUID | None
    editable: bool


class HistoryRead(BaseModel):
    """One account and its history in one month."""

    account: AccountRead
    month: str
    closed: bool
    entries: list[EntryRead]


class MoneyInRequest(BaseModel):
    """Money that reached an account: from outside (income) or from another own account."""

    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    source: str = Field(min_length=1, max_length=80)
    received_on: date
    from_account_id: uuid.UUID | None = None


class MoveRequest(BaseModel):
    """Money moved between two accounts: neither income nor spending."""

    from_account_id: uuid.UUID
    to_account_id: uuid.UUID
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    moved_on: date
    name: str | None = Field(None, max_length=80)


class MoveChange(BaseModel):
    """A correction to a move of this month."""

    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    moved_on: date


class IncomeChange(BaseModel):
    """A correction to an income on an account this month."""

    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    received_on: date


class AdjustRequest(BaseModel):
    """What the bank says is on the account now."""

    balance: Decimal = Field(max_digits=12, decimal_places=2)


class OccurrenceRequest(BaseModel):
    """This month's bill or transfer made by a rule, as it really went; 0 skips it."""

    kind: Literal["bill", "transfer"]
    amount: Decimal = Field(ge=0, max_digits=12, decimal_places=2)


class ConfirmRequest(BaseModel):
    """What an "about" income really brought this month."""

    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)


class TransferRuleRequest(BaseModel):
    """Money moved every month by itself, on `day` (any day: the 1st)."""

    from_account_id: uuid.UUID
    to_account_id: uuid.UUID
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    day: int | None = Field(None, ge=1, le=31)
    name: str | None = Field(None, max_length=80)


class TransferRuleRead(BaseModel):
    """A monthly transfer and when it started."""

    id: uuid.UUID
    name: str
    amount: Decimal
    day: int | None
    starts_on: date
    from_account_id: uuid.UUID
    to_account_id: uuid.UUID

    model_config = ConfigDict(from_attributes=True)


class ExpectedRead(BaseModel):
    """An "about" income whose day has come, waiting for what really came."""

    source_id: uuid.UUID
    account_id: uuid.UUID
    name: str
    day: date
    amount: Decimal
