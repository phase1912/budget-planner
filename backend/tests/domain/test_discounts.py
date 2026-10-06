"""Discount lines stay lines of their own, filed with the product they reduce ("Rabat", "OPUST")."""

from decimal import Decimal
from typing import Any

from app.domain.discounts import (
    discounted_products,
    dominant_category,
    file_discounts_with_products,
)
from app.domain.receipt_totals import lines_match_total

GROCERIES = "c-groceries"
DRINKS = "c-drinks"


def _line(name: str, total: str, **extra: Any) -> dict[str, Any]:
    return {"name": name, "quantity": "1", "unit_price": total, "total_price": total, **extra}


def test_a_discount_stays_its_own_line_and_takes_its_products_category() -> None:
    items = [
        _line("Olej 3l", "33.98", category_id=GROCERIES, category_confidence=95),
        _line("Rabat", "-10.04", category_id="c-other", category_confidence=40),
        _line("Woda", "2.49", category_id=DRINKS, category_confidence=90),
    ]

    filed = file_discounts_with_products(items)

    assert [(i["name"], i["total_price"], i["category_id"]) for i in filed] == [
        ("Olej 3l", "33.98", GROCERIES),
        ("Rabat", "-10.04", GROCERIES),
        ("Woda", "2.49", DRINKS),
    ]
    assert filed[1]["category_confidence"] == 95
    assert items[1]["category_id"] == "c-other"


def test_the_lines_add_up_to_what_was_paid_with_the_discount_counted() -> None:
    items = [_line("A", "8.99"), _line("OPUST", "-4.99"), _line("B", "6.58")]

    paid = sum(Decimal(i["total_price"]) for i in file_discounts_with_products(items))

    assert paid == Decimal("10.58")


def test_several_discounts_under_one_product_all_reduce_it() -> None:
    items = [_line("Woda", "29,88"), _line("OPUST", "-9,96"), _line("Rabat", "-1,00")]

    assert discounted_products(items) == {1: 0, 2: 0}


def test_a_discount_with_no_product_above_it_is_kept_as_it_is() -> None:
    items = [_line("Rabat", "-2.00", category_id=None), _line("Chleb", "4.50")]

    assert discounted_products(items) == {}
    assert file_discounts_with_products(items) == items


def test_a_discount_never_reaches_into_another_photos_product() -> None:
    items = [_line("Olej", "33.98", file_id="p1"), _line("OPUST", "-10.04", file_id="p2")]

    assert discounted_products(items) == {}


def test_unreadable_and_zero_lines_are_neither_discounts_nor_products() -> None:
    items = [_line("A", "5.00"), _line("ZERO", "0.00"), _line("B", "abc"), "not a line"]

    assert file_discounts_with_products(items) == items


def test_a_grosz_of_rounding_still_matches_but_more_does_not() -> None:
    assert lines_match_total(Decimal("188.03"), Decimal("188.02"))
    assert lines_match_total(Decimal("188.01"), Decimal("188.02"))
    assert not lines_match_total(Decimal("188.04"), Decimal("188.02"))
    assert not lines_match_total(Decimal("226.26"), Decimal("188.02"))


def test_a_whole_receipt_discount_goes_to_the_category_with_most_spend() -> None:
    lines = [
        ("dairy", Decimal("17.97")),
        ("bakery", Decimal("20.00")),
        ("dairy", Decimal("16.47")),
        (None, Decimal("50.00")),
        ("bakery", Decimal("-5.00")),
    ]

    assert dominant_category(lines) == "dairy"
    assert dominant_category([(None, Decimal("3.00"))]) is None
