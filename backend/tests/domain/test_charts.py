"""The statistics chart the server hands the client ready to draw (BRD E6)."""

import uuid
from decimal import Decimal
from itertools import pairwise

import pytest

from app.domain.charts import CHART_CATEGORIES, build_chart, nice_scale
from app.domain.statistics import CategoryTotal, compare_categories, rank_categories


@pytest.mark.parametrize(
    ("peak", "top", "step"),
    [
        ("742.60", "800", "200"),
        ("812.40", "1000", "250"),
        ("160", "200", "50"),
        ("9", "10", "2.5"),
        ("0.79", "0.8", "0.2"),
    ],
)
def test_the_axis_tops_out_at_a_round_number_in_round_steps(peak: str, top: str, step: str) -> None:
    scale_max, ticks = nice_scale(Decimal(peak))
    assert scale_max == Decimal(top)
    assert ticks[0] == 0 and ticks[-1] == Decimal(top)
    assert {b - a for a, b in pairwise(ticks)} == {Decimal(step)}


def test_a_period_with_nothing_to_draw_still_has_an_axis() -> None:
    assert nice_scale(Decimal(0)) == (Decimal(1), [Decimal(0), Decimal(1)])


def _total(name: str, amount: str) -> CategoryTotal:
    return CategoryTotal(uuid.uuid4(), name, 1, Decimal(amount))


def test_bars_come_as_heights_of_the_scale_both_periods_side_by_side() -> None:
    groceries, dining = _total("Groceries", "742.60"), _total("Dining", "386.00")
    now = rank_categories([groceries, dining])
    before = [
        CategoryTotal(groceries.category_id, "Groceries", 1, Decimal("812.40")),
        CategoryTotal(dining.category_id, "Dining", 1, Decimal("298.00")),
    ]

    chart = build_chart(now, compare_categories(now, before))

    assert chart.scale_max == Decimal(1000)
    assert [(g.name, g.current.height, g.previous and g.previous.height) for g in chart.groups] == [
        ("Groceries", Decimal("74.3"), Decimal("81.2")),
        ("Dining", Decimal("38.6"), Decimal("29.8")),
    ]


def test_without_a_comparison_each_category_has_one_bar() -> None:
    chart = build_chart(rank_categories([_total("Groceries", "10.00")]))
    assert chart.groups[0].previous is None
    assert chart.groups[0].current.height == Decimal("100.0")


def test_a_refund_draws_no_bar_below_the_axis() -> None:
    chart = build_chart(rank_categories([_total("Groceries", "10.00"), _total("Other", "-3.00")]))
    assert chart.groups[-1].current == type(chart.groups[-1].current)(Decimal("-3.00"), Decimal(0))


def test_only_the_biggest_categories_are_drawn_and_the_rest_are_counted() -> None:
    many = [_total(f"C{i}", str(100 - i)) for i in range(CHART_CATEGORIES + 3)]

    chart = build_chart(rank_categories(many))

    assert (len(chart.groups), chart.hidden) == (CHART_CATEGORIES, 3)
    assert chart.groups[0].name == "C0"
