"""What came in during a month (F23.10)."""

import calendar
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from enum import StrEnum


class IncomeKind(StrEnum):
    """What a sum that came in was."""

    SALARY = "salary"
    SIDE = "side"
    REFUND = "refund"
    OTHER = "other"


class IncomeChannel(StrEnum):
    """How it reached the service: typed in, or read from a document (F23.11)."""

    MANUAL = "manual"
    DOCUMENT = "document"


HUNDRED = Decimal(100)
CENT = Decimal("0.01")
TAXED_KINDS = frozenset({IncomeKind.SALARY, IncomeKind.SIDE})
"""Kinds taxed unless the user says otherwise: earnings. A gift, a refund or something
sold is not — whatever its size, which is why the default goes by kind, not amount."""


@dataclass(frozen=True)
class TaxRule:
    """What a user who pays their own taxes sets aside (F23.16): a share of each taxed
    income, and a fixed sum once a month (a social contribution, a flat tax)."""

    rate: Decimal
    fixed: Decimal

    def on(self, taxed_amount: Decimal) -> Decimal:
        """The share set aside from `taxed_amount`, to the grosz."""
        return (taxed_amount * self.rate / HUNDRED).quantize(CENT)


def taxed_by_default(kind: IncomeKind) -> bool:
    """Whether a new entry of `kind` is taxed when the user did not say."""
    return kind in TAXED_KINDS


@dataclass(frozen=True)
class MonthIncome:
    """A month's income and whether it is entered or only the usual amount standing in.

    `total` is what came in, as it came; `taxes` what of it goes to taxes for a user who
    pays their own (zero otherwise); `net` what is left to live on.
    """

    total: Decimal | None
    entered: bool
    taxes: Decimal = Decimal("0.00")

    @property
    def net(self) -> Decimal | None:
        return None if self.total is None else self.total - self.taxes


def month_income(
    entries: Iterable[tuple[Decimal, bool]],
    usual: Decimal | None,
    taxes: TaxRule | None = None,
    recurring: Iterable[tuple[Decimal, bool]] = (),
) -> MonthIncome:
    """The month's income: its entries summed, else the account's usual income.

    `entries` are (amount, taxed) pairs. A month with nothing entered yet is not a month
    with no income — the usual amount stands in, marked as such, so "left to spend" is not
    wrong on the 1st; for a user who pays their own taxes it is taken as taxed. None when
    there is neither. With a `TaxRule`, the month's taxes are its share of the taxed
    entries plus the fixed sum, once — whether or not anything came in.

    `recurring` are the (amount, taxed) regular incomes running this month (F23.17): they
    count by themselves, and with them the usual income no longer stands in — entries come
    on top. A taxed one is taxed like a taxed entry.
    """
    listed = list(entries)
    regular_listed = list(recurring)
    regular = sum((amount for amount, _ in regular_listed), Decimal("0"))
    total: Decimal | None
    if listed or regular:
        total = regular + sum((amount for amount, _ in listed), Decimal("0"))
        taxed = sum(
            (amount for amount, is_taxed in [*listed, *regular_listed] if is_taxed), Decimal("0")
        )
        entered = True
    else:
        total, taxed, entered = usual, usual or Decimal("0"), False
    if taxes is None:
        return MonthIncome(total=total, entered=entered)
    return MonthIncome(total=total, entered=entered, taxes=taxes.on(taxed) + taxes.fixed)


@dataclass(frozen=True)
class Recurring:
    """A regular income or bill as the rules need it: how much, on which day, over which
    months (F23.17, F23.18)."""

    amount: Decimal
    day: int | None
    starts_on: date
    ends_on: date | None
    taxed: bool = False

    def runs_in(self, first_day: date) -> bool:
        """Whether it counts in the month starting `first_day`: from its first month to
        its last, both included."""
        start = self.starts_on.replace(day=1)
        return start <= first_day and (self.ends_on is None or self.ends_on >= first_day)

    def arrives_in(self, first_day: date) -> date:
        """The day it arrives in that month; a 31st in a shorter month is its last day."""
        last = calendar.monthrange(first_day.year, first_day.month)[1]
        return first_day.replace(day=min(self.day or 1, last))


def regular_since(
    incomes: Iterable[Recurring], since: date, today: date, *, taxed_only: bool = False
) -> Decimal:
    """What regular incomes brought — or regular bills took — from `since` to `today`,
    both included: each month's amount once its day has come, so the balance moves on the
    day the salary arrives or the rent goes. With `taxed_only`, only those the user's tax
    comes out of — what taxes are owed on."""
    total = Decimal("0")
    month = since.replace(day=1)
    rules = [i for i in incomes if i.taxed or not taxed_only]
    while month <= today:
        for income in rules:
            if income.runs_in(month) and since <= income.arrives_in(month) <= today:
                total += income.amount
        month = (month.replace(day=28) + timedelta(days=4)).replace(day=1)
    return total
