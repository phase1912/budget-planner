"""A budget period is one calendar month (BRD D2, ADR-0009)."""

from datetime import UTC, datetime

import pytest

from app.domain.budget import BudgetMonth


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
