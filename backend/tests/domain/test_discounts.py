"""Discount lines fold into the item they reduce (Polish "OPUST" lines)."""

from typing import Any

from app.domain.discounts import fold_discounts


def _line(name: str, total: str, **extra: Any) -> dict[str, Any]:
    return {"name": name, "quantity": "1", "unit_price": total, "total_price": total, **extra}


def test_a_discount_reduces_the_item_printed_above_it() -> None:
    items = [_line("Olej 3l", "33.98"), _line("OPUST", "-10.04"), _line("Kawa", "49.98")]

    folded, _ = fold_discounts(items)

    assert [(i["name"], i["total_price"], i.get("discount")) for i in folded] == [
        ("Olej 3l", "23.94", "10.04"),
        ("Kawa", "49.98", None),
    ]
    assert folded[0]["unit_price"] == "33.98"


def test_the_receipt_still_adds_up_to_the_same_total() -> None:
    items = [
        _line("A", "8.99"),
        _line("OPUST", "-4.99"),
        _line("B", "6.58"),
        _line("OPUST", "-0.40"),
    ]

    folded, _ = fold_discounts(items)

    assert sum(float(i["total_price"]) for i in folded) == sum(
        float(i["total_price"]) for i in items
    )


def test_comma_decimals_and_repeated_discounts_on_one_item_are_handled() -> None:
    items = [_line("Woda", "29,88"), _line("OPUST", "-9,96"), _line("OPUST 2", "-1,00")]

    [water], _ = fold_discounts(items)

    assert (water["total_price"], water["discount"]) == ("18.92", "10.96")


def test_a_discount_with_no_product_above_it_is_kept_rather_than_lost() -> None:
    items = [_line("OPUST", "-2.00"), _line("Chleb", "4.50")]

    assert fold_discounts(items)[0] == items


def test_unreadable_and_zero_lines_pass_through() -> None:
    items = [_line("A", "5.00"), _line("UNKNOWN", "0.00"), _line("B", "abc"), "not a line"]

    assert fold_discounts(items)[0] == items


def test_a_discount_never_crosses_into_another_photos_item() -> None:
    items = [_line("Olej", "33.98", file_id="p1"), _line("OPUST", "-10.04", file_id="p2")]

    assert fold_discounts(items)[0] == items


def test_position_matches_are_renumbered_and_those_on_discount_lines_dropped() -> None:
    """Both photos show "Kawa" and its discount; each copy folds into its own photo's Kawa."""
    items = [
        _line("Kawa", "49.98", file_id="p1"),
        _line("OPUST", "-14.00", file_id="p1"),
        _line("Kawa", "49.98", file_id="p2"),
        _line("OPUST", "-14.00", file_id="p2"),
        _line("Chleb", "4.50", file_id="p2"),
    ]
    matches = [
        {"item_a_index": 0, "item_b_index": 2, "result": "same"},
        {"item_a_index": 1, "item_b_index": 3, "result": "same"},
    ]

    folded, renumbered = fold_discounts(items, matches)

    assert [(i["name"], i["total_price"]) for i in folded] == [
        ("Kawa", "35.98"),
        ("Kawa", "35.98"),
        ("Chleb", "4.50"),
    ]
    assert renumbered == [{"item_a_index": 0, "item_b_index": 1, "result": "same"}]
