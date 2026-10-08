"""A receipt's lines are made to agree with its total by rule, before anyone is asked (A9)."""

from typing import Any

from app.domain.receipt_reconciliation import (
    Reconciliation,
    accepts_recheck,
    reconcile_by_rules,
)


def _line(name: str, total: str, quantity: str = "1", unit: str | None = None) -> dict[str, Any]:
    return {"name": name, "quantity": quantity, "unit_price": unit or total, "total_price": total}


def _reading(total: str, *lines: dict[str, Any]) -> dict[str, Any]:
    return {"receipt_total": total, "line_items": list(lines), "position_matches": []}


def test_a_bottle_deposit_read_as_a_line_makes_the_total_the_amount_paid() -> None:
    """The Biedronka receipt: SUMA PLN 185,02, kaucja 3,00, DO ZAPŁATY 188,02."""
    reading = _reading(
        "185,02",
        _line("Zakupy", "185.02"),
        _line("But Plastik kaucja", "3.00", quantity="6", unit="0.50"),
    )

    how, fixed = reconcile_by_rules(reading) or (None, None)

    assert how == Reconciliation.DEPOSIT
    assert fixed is not None and fixed["receipt_total"] == "188.02"
    assert reading["receipt_total"] == "185,02"


def test_a_discount_read_without_its_minus_is_flipped() -> None:
    reading = _reading("10.00", _line("Awokado", "13.98"), _line("OPUST", "3.98"))

    how, fixed = reconcile_by_rules(reading) or (None, None)

    assert how == Reconciliation.DISCOUNT_SIGN
    assert fixed is not None and fixed["line_items"][1]["total_price"] == "-3.98"


def test_a_misread_line_total_is_taken_from_quantity_times_price() -> None:
    reading = _reading(
        "26.47", _line("Jogurt", "16.17", quantity="3", unit="5.49"), _line("Chleb", "10.00")
    )

    how, fixed = reconcile_by_rules(reading) or (None, None)

    assert how == Reconciliation.LINE_ARITHMETIC
    assert fixed is not None and fixed["line_items"][0]["total_price"] == "16.47"


def test_a_gap_no_rule_explains_is_left_alone() -> None:
    assert reconcile_by_rules(_reading("20.00", _line("Chleb", "10.00"))) is None


def test_a_reading_that_already_agrees_needs_nothing() -> None:
    assert reconcile_by_rules(_reading("10.00", _line("Chleb", "10.00"))) is None


def test_a_second_reading_counts_only_if_it_agrees_with_the_same_total() -> None:
    before = _reading("20.00", _line("Chleb", "10.00"))
    fixed_lines = _reading("20.00", _line("Chleb", "10.00"), _line("Mleko", "10.00"))
    moved_total = _reading("10.00", _line("Chleb", "10.00"))

    assert accepts_recheck(before, fixed_lines)
    assert not accepts_recheck(before, moved_total)


def test_a_deposit_listed_twice_loses_its_repeat() -> None:
    """The same receipt as read by a small model: the section heading taken as a line."""
    reading = _reading(
        "188.02",
        _line("Zakupy", "185.02"),
        _line("OPAKOWANIA ZWROTNE WYDANIA", "3.00", quantity="6", unit="0.50"),
        _line("But Plastik kaucja", "3.00"),
    )

    how, fixed = reconcile_by_rules(reading) or (None, None)

    assert how == Reconciliation.REPEATED_LINE
    assert fixed is not None
    assert [line["name"] for line in fixed["line_items"]] == ["Zakupy", "But Plastik kaucja"]


def test_two_equal_products_are_never_taken_for_a_repeat() -> None:
    reading = _reading("10.00", _line("Woda", "5.00"), _line("Woda", "5.00"), _line("Woda", "5.00"))

    assert reconcile_by_rules(reading) is None
