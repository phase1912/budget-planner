"""The one date-range rule: whole days, both ends included (BRD E2)."""

from datetime import UTC, date, datetime

import pytest

from app.domain.budget import BudgetMonth
from app.domain.periods import DateRange


def test_a_range_runs_from_midnight_on_its_first_day_to_midnight_after_its_last() -> None:
    days = DateRange(date(2026, 7, 10), date(2026, 7, 24))
    assert (days.lower, days.upper) == (
        datetime(2026, 7, 10, tzinfo=UTC),
        datetime(2026, 7, 25, tzinfo=UTC),
    )


def test_a_single_day_is_a_range_of_one() -> None:
    day = DateRange(date(2026, 7, 10), date(2026, 7, 10))
    assert day.upper == datetime(2026, 7, 11, tzinfo=UTC)


def test_a_month_is_every_one_of_its_days_leap_february_included() -> None:
    assert DateRange.of_month(BudgetMonth(2028, 2)) == DateRange(
        date(2028, 2, 1), date(2028, 2, 29)
    )
    assert DateRange.of_month(BudgetMonth(2026, 12)) == DateRange(
        date(2026, 12, 1), date(2026, 12, 31)
    )


def test_a_range_that_ends_before_it_starts_is_refused() -> None:
    with pytest.raises(ValueError, match="ends"):
        DateRange(date(2026, 7, 24), date(2026, 7, 10))
