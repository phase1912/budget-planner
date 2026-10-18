"""Spending day by day (F23.4)."""

from datetime import date
from decimal import Decimal

from app.domain.daily_spend import daily_spend
from app.domain.periods import DateRange

WEEK = DateRange(date(2026, 10, 5), date(2026, 10, 11))


def test_every_day_is_listed_and_a_quiet_one_is_zero() -> None:
    spend = daily_spend(WEEK, {date(2026, 10, 6): Decimal("40.00")}, today=date(2026, 10, 20))

    assert spend.days[0].day == date(2026, 10, 5)
    assert len(spend.days) == 7
    assert spend.days[1].total == Decimal("40.00")
    assert spend.days[0].total == Decimal("0")
    assert spend.total == Decimal("40.00")


def test_a_running_period_averages_over_the_days_passed_not_the_days_listed() -> None:
    spend = daily_spend(
        WEEK,
        {date(2026, 10, 5): Decimal("30.00"), date(2026, 10, 6): Decimal("15.00")},
        today=date(2026, 10, 7),
    )

    assert spend.average == Decimal("15.00")
    assert len(spend.days) == 7


def test_a_period_still_ahead_averages_without_dividing_by_zero() -> None:
    spend = daily_spend(WEEK, {}, today=date(2026, 10, 1))

    assert spend.average == Decimal("0.00")
