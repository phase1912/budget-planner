"""Ranking categories and their shares of a period's spend (BRD E1, E4)."""

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from app.domain.statistics import CategoryTotal, StatisticsPeriod, rank_categories


def _total(name: str, amount: str, items: int = 1) -> CategoryTotal:
    return CategoryTotal(uuid.uuid4(), name, items, Decimal(amount))


def test_categories_are_ranked_by_spend_with_their_share_and_item_count() -> None:
    ranked = rank_categories(
        [_total("Dining", "386.00", 14), _total("Groceries", "742.60", 68), _total("Pets", "71.40")]
    )

    assert [(c.name, c.share, c.item_count) for c in ranked] == [
        ("Groceries", Decimal("61.9"), 68),
        ("Dining", Decimal("32.2"), 14),
        ("Pets", Decimal("6.0"), 1),
    ]


def test_equal_spend_is_ordered_by_name_so_the_ranking_is_stable() -> None:
    ranked = rank_categories([_total("Transport", "10.00"), _total("Health", "10.00")])
    assert [c.name for c in ranked] == ["Health", "Transport"]


def test_a_period_of_refunds_only_gives_no_share_rather_than_dividing_by_zero() -> None:
    ranked = rank_categories([_total("Groceries", "-4.00"), _total("Other", "4.00")])
    assert [c.share for c in ranked] == [Decimal(0), Decimal(0)]


def test_a_period_covers_its_last_day_to_the_final_microsecond() -> None:
    period = StatisticsPeriod(date(2026, 7, 10), date(2026, 7, 24))
    assert period.first_instant == datetime(2026, 7, 10, tzinfo=UTC)
    assert period.last_instant == datetime(2026, 7, 24, 23, 59, 59, 999999, tzinfo=UTC)


def test_a_period_that_ends_before_it_starts_is_refused() -> None:
    with pytest.raises(ValueError, match="ends"):
        StatisticsPeriod(date(2026, 7, 24), date(2026, 7, 10))
