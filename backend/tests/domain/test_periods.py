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


@pytest.mark.parametrize(
    ("start", "end", "before_start", "before_end"),
    [
        # A running month meets the same days of the month before.
        ((2026, 7, 1), (2026, 7, 27), (2026, 6, 1), (2026, 6, 27)),
        # A whole month meets the whole month before, however long each is.
        ((2026, 8, 1), (2026, 8, 31), (2026, 7, 1), (2026, 7, 31)),
        ((2026, 3, 1), (2026, 3, 31), (2026, 2, 1), (2026, 2, 28)),
        # A day the shorter month lacks falls back to its last day.
        ((2026, 3, 1), (2026, 3, 30), (2026, 2, 1), (2026, 2, 28)),
        # Three months so far meet the three before, to the same day.
        ((2026, 7, 1), (2026, 9, 27), (2026, 4, 1), (2026, 6, 27)),
        # Across a year.
        ((2026, 1, 1), (2026, 1, 15), (2025, 12, 1), (2025, 12, 15)),
        # Any other range meets as many days right before it.
        ((2026, 7, 10), (2026, 7, 24), (2026, 6, 25), (2026, 7, 9)),
    ],
)
def test_a_period_is_compared_like_for_like(
    start: tuple[int, int, int],
    end: tuple[int, int, int],
    before_start: tuple[int, int, int],
    before_end: tuple[int, int, int],
) -> None:
    previous = DateRange(date(*start), date(*end)).previous()
    assert previous == DateRange(date(*before_start), date(*before_end))


def test_only_a_range_from_a_1st_that_stops_short_of_a_month_end_stops_mid_month() -> None:
    assert DateRange(date(2026, 7, 1), date(2026, 7, 27)).stops_mid_month
    assert DateRange(date(2026, 7, 1), date(2026, 9, 27)).stops_mid_month
    assert not DateRange(date(2026, 8, 1), date(2026, 8, 31)).stops_mid_month
    assert not DateRange(date(2026, 7, 10), date(2026, 7, 24)).stops_mid_month
