"""Ranking categories and their shares of a period's spend (BRD E1, E4)."""

import uuid
from decimal import Decimal

from app.domain.statistics import CategoryTotal, compare_categories, rank_categories


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


def test_each_category_carries_its_change_in_amount_and_percent() -> None:
    """E3, with the design's numbers: Groceries down 8.6%, Dining up 29.5%."""
    groceries, dining = uuid.uuid4(), uuid.uuid4()
    now = rank_categories(
        [
            CategoryTotal(groceries, "Groceries", 68, Decimal("742.60")),
            CategoryTotal(dining, "Dining", 14, Decimal("386.00")),
        ]
    )
    before = [
        CategoryTotal(groceries, "Groceries", 70, Decimal("812.40")),
        CategoryTotal(dining, "Dining", 11, Decimal("298.00")),
    ]

    rows = compare_categories(now, before)

    assert [(r.standing.name, r.change, r.change_percent) for r in rows] == [
        ("Groceries", Decimal("-69.80"), Decimal("-8.6")),
        ("Dining", Decimal("88.00"), Decimal("29.5")),
    ]


def test_a_new_category_has_no_percentage_rather_than_a_division_by_zero() -> None:
    [row] = compare_categories(rank_categories([_total("Pets", "20.00")]), [])
    assert (row.previous_total, row.change, row.change_percent) == (
        Decimal(0),
        Decimal("20.00"),
        None,
    )


def test_a_category_spent_on_only_before_stays_listed_at_zero_after_the_ranked_ones() -> None:
    pets = _total("Pets", "30.00")
    now = rank_categories([_total("Groceries", "10.00")])

    rows = compare_categories(now, [pets])

    assert [(r.standing.name, r.standing.total, r.change_percent) for r in rows] == [
        ("Groceries", Decimal("10.00"), None),
        ("Pets", Decimal(0), Decimal("-100.0")),
    ]
