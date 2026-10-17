"""What came in during a month (F23.10)."""

from collections.abc import Iterable
from dataclasses import dataclass
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


@dataclass(frozen=True)
class MonthIncome:
    """A month's income and whether it is entered or only the usual amount standing in."""

    total: Decimal | None
    entered: bool


def month_income(amounts: Iterable[Decimal], usual: Decimal | None) -> MonthIncome:
    """The month's income: its entries summed, else the account's usual income.

    A month with nothing entered yet is not a month with no income — the usual amount
    stands in, marked as such, so "left to spend" is not wrong on the 1st. None when
    there is neither.
    """
    entries = list(amounts)
    if entries:
        return MonthIncome(total=sum(entries, Decimal("0")), entered=True)
    return MonthIncome(total=usual, entered=False)
