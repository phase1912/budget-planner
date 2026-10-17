"""A month's income (F23.10)."""

from decimal import Decimal

from app.domain.income import month_income


def test_a_month_with_entries_counts_them() -> None:
    result = month_income([Decimal("6200"), Decimal("600")], usual=Decimal("6800"))
    assert result.total == Decimal("6800") and result.entered


def test_a_month_without_entries_shows_the_usual_income_marked_as_such() -> None:
    result = month_income([], usual=Decimal("6800"))
    assert result.total == Decimal("6800") and not result.entered


def test_no_entries_and_no_usual_income_is_unknown_not_zero() -> None:
    assert month_income([], usual=None).total is None
