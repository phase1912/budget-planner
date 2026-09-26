"""A budget period is one calendar month (BRD D2, ADR-0009)."""

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from app.domain.budget import BudgetMonth, limit_usage, may_finalise


def test_a_month_runs_from_its_first_instant_to_the_next_months_first() -> None:
    september = BudgetMonth(2026, 9)
    assert september.start == datetime(2026, 9, 1, tzinfo=UTC)
    assert september.end == datetime(2026, 10, 1, tzinfo=UTC)


def test_december_ends_where_the_next_year_begins() -> None:
    assert BudgetMonth(2026, 12).end == datetime(2027, 1, 1, tzinfo=UTC)


@pytest.mark.parametrize(("year", "month"), [(2026, 0), (2026, 13), (1969, 5)])
def test_a_month_that_does_not_exist_is_refused(year: int, month: int) -> None:
    with pytest.raises(ValueError):
        BudgetMonth(year, month)


def test_the_current_month_is_incomplete_and_counts_the_days_so_far() -> None:
    """D4: 27 July is month-to-date, 27 of 31 days in."""
    progress = BudgetMonth(2026, 7).progress(date(2026, 7, 27))
    assert (progress.is_complete, progress.days_elapsed, progress.days) == (False, 27, 31)


def test_a_month_is_complete_the_day_after_its_last() -> None:
    assert BudgetMonth(2026, 7).progress(date(2026, 7, 31)).is_complete is False
    assert BudgetMonth(2026, 7).progress(date(2026, 8, 1)).is_complete is True


def test_a_past_month_counts_all_its_days_and_february_knows_leap_years() -> None:
    assert BudgetMonth(2028, 2).progress(date(2028, 5, 1)).days_elapsed == 29
    assert BudgetMonth(2026, 2).progress(date(2026, 5, 1)).days_elapsed == 28


def test_a_month_that_has_not_begun_has_no_days_behind_it() -> None:
    progress = BudgetMonth(2026, 10).progress(date(2026, 9, 26))
    assert (progress.is_complete, progress.days_elapsed) == (False, 0)


def test_a_month_may_be_finalised_once_it_has_ended_in_the_earliest_timezone() -> None:
    """ADR-0010: September is over in Kiribati (UTC+14) from 10:00 UTC on 30 September."""
    september = BudgetMonth(2026, 9)
    assert may_finalise(september, datetime(2026, 9, 30, 9, 59, tzinfo=UTC)) is False
    assert may_finalise(september, datetime(2026, 9, 30, 10, 0, tzinfo=UTC)) is True


def test_spend_is_shown_as_a_share_of_the_limit_with_what_is_left() -> None:
    """D7, as the BRD's own example: 1 800 of a 3 000 limit is 60%."""
    usage = limit_usage(Decimal("1800.00"), Decimal("3000.00"))
    assert usage is not None
    assert (usage.percent, usage.remaining, usage.is_over) == (60, Decimal("1200.00"), False)


def test_spend_past_the_limit_reads_over_100_percent_and_by_how_much() -> None:
    """Over the limit is not clamped at full: 3 248 of 3 000 is 108%, 248 over."""
    usage = limit_usage(Decimal("3248.00"), Decimal("3000.00"))
    assert usage is not None
    assert (usage.percent, usage.remaining, usage.is_over) == (108, Decimal("-248.00"), True)


@pytest.mark.parametrize(
    ("total", "percent", "over"),
    [("2999.99", 99, False), ("3000.00", 100, False), ("-12.00", 0, False)],
)
def test_the_share_is_rounded_down_and_never_below_zero(
    total: str, percent: int, over: bool
) -> None:
    """Still under the limit never reads 100%; reaching it exactly is not over."""
    usage = limit_usage(Decimal(total), Decimal("3000.00"))
    assert usage is not None
    assert (usage.percent, usage.is_over) == (percent, over)


def test_no_limit_means_no_share_at_all() -> None:
    assert limit_usage(Decimal("1800.00"), None) is None
