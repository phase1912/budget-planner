"""The rules accounts live by (F23.15)."""

from datetime import date
from decimal import Decimal

import pytest

from app.domain.accounts import first_month, is_closed, tax_on


@pytest.mark.parametrize(
    ("day", "expected"),
    [
        (5, date(2026, 11, 1)),  # the 5th has passed on the 18th
        (18, date(2026, 10, 1)),  # today still counts
        (20, date(2026, 10, 1)),
        (None, date(2026, 10, 1)),  # any day: this month
    ],
)
def test_a_rule_never_posts_on_a_day_already_past(day: int | None, expected: date) -> None:
    assert first_month(day, date(2026, 10, 18)) == expected


def test_a_31st_in_a_shorter_month_has_not_passed_before_its_last_day() -> None:
    assert first_month(31, date(2026, 2, 27)) == date(2026, 2, 1)


def test_only_this_months_entries_stay_open() -> None:
    today = date(2026, 10, 18)
    assert not is_closed(date(2026, 10, 1), today)
    assert is_closed(date(2026, 9, 30), today)


def test_only_a_taxed_account_sets_anything_aside() -> None:
    assert tax_on(Decimal("10000.00"), Decimal("5")) == Decimal("500.00")
    assert tax_on(Decimal("1480.00"), Decimal("5")) == Decimal("74.00")
    assert tax_on(Decimal("10000.00"), None) == Decimal("0.00")
