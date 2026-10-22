"""Where a savings or lifestyle goal stands (F8.11.1, F8.11.2)."""

from datetime import date
from decimal import Decimal

from app.domain.goal_progress import LifestyleProgress, SavingsProgress, months_left

TODAY = date(2026, 10, 22)


def test_the_months_left_count_this_one_and_none_once_the_date_is_past() -> None:
    assert months_left(TODAY, date(2027, 6, 30)) == 9
    assert months_left(TODAY, date(2026, 10, 31)) == 1
    assert months_left(TODAY, date(2026, 9, 30)) == 0


def test_a_holiday_by_june_says_what_is_saved_and_what_is_needed_a_month() -> None:
    """The F8.11 demo: 3 000 by June with 1 200 saved — 40%, 200 a month for 9 months."""
    holiday = SavingsProgress(Decimal(1200), Decimal(3000), date(2027, 6, 30), TODAY)

    assert (holiday.percent, holiday.left, holiday.needed_per_month) == (
        40,
        Decimal(1800),
        Decimal("200.00"),
    )
    assert (holiday.reached, holiday.overdue) == (False, False)


def test_a_goal_past_its_date_short_of_the_money_is_overdue_and_needs_no_rate() -> None:
    late = SavingsProgress(Decimal(500), Decimal(3000), date(2026, 9, 30), TODAY)

    assert (late.overdue, late.needed_per_month) == (True, None)


def test_a_goal_reached_is_whole_and_never_overdue() -> None:
    done = SavingsProgress(Decimal(3500), Decimal(3000), date(2026, 9, 30), TODAY)

    assert (done.reached, done.percent, done.overdue, done.left) == (True, 100, False, Decimal(0))


def test_a_goal_without_a_date_has_no_rate_to_keep() -> None:
    assert SavingsProgress(Decimal(0), Decimal(100), None, TODAY).needed_per_month is None


def test_a_lifestyle_month_is_compared_with_the_months_before() -> None:
    assert LifestyleProgress(Decimal(60), Decimal(80)).change_percent == -25
    assert LifestyleProgress(Decimal(60), Decimal(0)).change_percent is None
