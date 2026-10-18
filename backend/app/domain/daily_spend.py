"""Spending day by day over a period (F23.4)."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from app.domain.periods import DateRange

CENT = Decimal("0.01")


@dataclass(frozen=True)
class DaySpend:
    """What was paid on one day."""

    day: date
    total: Decimal


@dataclass(frozen=True)
class DailySpend:
    """Every day of a period with what was paid on it, and the period's daily average."""

    days: list[DaySpend]
    total: Decimal
    average: Decimal


def daily_spend(period: DateRange, totals: Mapping[date, Decimal], today: date) -> DailySpend:
    """Each day of `period` with its spending, a day without purchases as zero.

    The average divides by the days that have passed — up to `today` when the period is
    still running — so a month is not made to look thriftier on the 3rd than it is. Days
    after `today` are listed, empty, so a chart keeps the month's shape.
    """
    days = [
        DaySpend(day, totals.get(day, Decimal("0")))
        for day in (period.start + timedelta(days=n) for n in range(period.days))
    ]
    total = sum((d.total for d in days), Decimal("0"))
    passed = sum(1 for d in days if d.day <= today) or 1
    return DailySpend(days, total, (total / passed).quantize(CENT))
