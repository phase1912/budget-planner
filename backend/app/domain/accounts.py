"""Where the money is: accounts, the money between them and the rules that move it (F23.15)."""

import calendar
import uuid
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from enum import StrEnum

CENT = Decimal("0.01")
HUNDRED = Decimal(100)
COMMON_TAX_RATES = (Decimal(5), Decimal(6), Decimal(12))
"""Rates offered on a business account; any other one may be typed."""


class AccountKind(StrEnum):
    """What an account is for: everyday money, a business, or savings kept as an amount."""

    PERSONAL = "personal"
    BUSINESS = "business"
    DEPOSIT = "deposit"


class MoveKind(StrEnum):
    """Money that leaves or reaches an account without being income from outside.

    A transfer goes between two of the household's accounts and is neither income nor
    spending; a bill leaves one account; an adjustment corrects one to what the bank says.
    """

    TRANSFER = "transfer"
    BILL = "bill"
    ADJUSTMENT = "adjustment"


def tax_on(amount: Decimal, rate: Decimal | None) -> Decimal:
    """What a business account sets aside from `amount` that came from outside, to the grosz.

    No rate, no tax: a personal account and a transfer between own accounts are never taxed.
    """
    if not rate:
        return Decimal("0.00")
    return (amount * rate / HUNDRED).quantize(CENT)


def first_month(day: int | None, today: date) -> date:
    """The first day of the first month a rule made `today` posts in (F23.15).

    A rule never posts on a day already past: one for a day before today starts next
    month. One with no day, or for today or later, starts this month.
    """
    this_month = today.replace(day=1)
    if day is None or min(day, _last_day(today)) >= today.day:
        return this_month
    return next_month(this_month)


def next_month(first_day: date) -> date:
    """The first day of the month after the one starting `first_day`."""
    return (first_day.replace(day=28) + timedelta(days=4)).replace(day=1)


def is_closed(day: date, today: date) -> bool:
    """Whether an entry on `day` belongs to a closed month: anything before this month.

    This month's entries can still be changed, as a bank's pending ones; earlier months
    are what the bank statement says and stay as they are (F23.15).
    """
    return day < today.replace(day=1)


def months_between(start: date, end: date) -> list[date]:
    """The first days of every month from `start`'s to `end`'s, both included."""
    months: list[date] = []
    month = start.replace(day=1)
    while month <= end:
        months.append(month)
        month = next_month(month)
    return months


def _last_day(day: date) -> int:
    return calendar.monthrange(day.year, day.month)[1]


class EntryKind(StrEnum):
    """What one line of an account's history is."""

    INCOME = "income"
    EXPECTED = "expected"
    TRANSFER_IN = "transfer_in"
    TRANSFER_OUT = "transfer_out"
    BILL = "bill"
    ADJUSTMENT = "adjustment"
    PURCHASES = "purchases"
    TAX_PAID = "tax_paid"


@dataclass(frozen=True)
class Entry:
    """One line of an account's history, as the balance counts it.

    `amount` is signed: money in is positive. An `upcoming` line (a rule's day still to
    come this month) and an `expected` one (an "about" income not yet confirmed) are
    shown but not counted. `ref` names what to change it through — ("income", id),
    ("move", id), ("bill", id), ("rule", id), ("source", id) — and is None for a sum the
    user cannot change here, such as a day's purchases.
    """

    account_id: uuid.UUID
    day: date
    kind: EntryKind
    name: str
    amount: Decimal
    tax: Decimal = Decimal("0.00")
    ref: tuple[str, uuid.UUID] | None = None
    by_rule: bool = False
    upcoming: bool = False
    count: int = 0
    author: str | None = None

    @property
    def counted(self) -> bool:
        """Whether the balance counts it: neither still to come nor only expected."""
        return not self.upcoming and self.kind != EntryKind.EXPECTED


def ledger_of(opening: Decimal, entries: list[Entry]) -> "Ledger":
    """Sum an account's counted entries into its ledger, from its opening amount."""
    ledger = Ledger(opening)
    for entry in entries:
        if not entry.counted:
            continue
        if entry.kind == EntryKind.INCOME:
            ledger.came_in += entry.amount
            ledger.taxes += entry.tax
        elif entry.kind == EntryKind.TRANSFER_IN:
            ledger.moved_in += entry.amount
        elif entry.kind == EntryKind.TRANSFER_OUT:
            ledger.moved_out -= entry.amount
        elif entry.kind == EntryKind.ADJUSTMENT:
            ledger.moved_in += entry.amount
        elif entry.kind == EntryKind.BILL:
            ledger.bills -= entry.amount
        elif entry.kind == EntryKind.PURCHASES:
            ledger.purchases -= entry.amount
        elif entry.kind == EntryKind.TAX_PAID:
            ledger.taxes_paid -= entry.amount
    return ledger


@dataclass
class Ledger:
    """What happened on one account from its opening day: the money in and out, by kind.

    `taxes` is what was set aside of `came_in` on a business account, still on it until
    paid; `balance` counts it, as a bank does.
    """

    opening: Decimal
    came_in: Decimal = Decimal("0.00")
    moved_in: Decimal = Decimal("0.00")
    moved_out: Decimal = Decimal("0.00")
    bills: Decimal = Decimal("0.00")
    purchases: Decimal = Decimal("0.00")
    taxes: Decimal = Decimal("0.00")
    taxes_paid: Decimal = Decimal("0.00")

    @property
    def balance(self) -> Decimal:
        """What is on the account now."""
        return (
            self.opening
            + self.came_in
            + self.moved_in
            - self.moved_out
            - self.bills
            - self.purchases
            - self.taxes_paid
        )

    @property
    def set_aside(self) -> Decimal:
        """Of the balance, what is still owed in taxes, never below zero."""
        return max(self.taxes - self.taxes_paid, Decimal("0.00"))
