"""Where a monthly money goal is heading this month (BRD F6, F7)."""

from datetime import date
from decimal import Decimal

from app.domain.goal_pace import pace


def test_the_month_is_carried_forward_at_the_rate_so_far() -> None:
    """1 800 spent by 27 July: 66.67 a day, so July finishes near 2 066.67."""
    goal_pace = pace(Decimal("1800"), Decimal("3000"), date(2026, 7, 27))

    assert (goal_pace.projected, goal_pace.day, goal_pace.days_in_month) == (
        Decimal("2066.67"),
        27,
        31,
    )
    assert goal_pace.on_track
    assert goal_pace.margin == Decimal("933.33")


def test_heading_over_the_cap_is_off_track_with_a_negative_margin() -> None:
    goal_pace = pace(Decimal("1500"), Decimal("3000"), date(2026, 2, 10))

    assert (goal_pace.projected, goal_pace.on_track) == (Decimal("4200.00"), False)
    assert goal_pace.margin == Decimal("-1200.00")


def test_on_the_last_day_the_projection_is_the_spend_itself() -> None:
    goal_pace = pace(Decimal("2999.99"), Decimal("3000"), date(2026, 9, 30))

    assert (goal_pace.projected, goal_pace.on_track) == (Decimal("2999.99"), True)


def test_finishing_exactly_on_the_cap_counts_as_on_track() -> None:
    assert pace(Decimal("1500"), Decimal("3000"), date(2026, 9, 15)).on_track
