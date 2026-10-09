"""Converting a foreign receipt into the account's currency (F11.7, ADR-0016)."""

from datetime import date
from decimal import Decimal
from typing import Any

import pytest

from app.domain.currency import (
    ExchangeRate,
    conversion_preview,
    convert,
    convert_extraction,
    convert_receipt,
    receipt_currency,
    unconverted,
)

UAH_PLN = ExchangeRate("UAH", "PLN", Decimal("0.0864"), date(2026, 10, 2), "NBP")


def test_an_amount_is_converted_to_the_cent_half_up() -> None:
    assert convert(Decimal("1197.00"), Decimal("0.0864")) == Decimal("103.42")
    assert convert(Decimal("0.125"), Decimal(1)) == Decimal("0.13")


def test_converted_lines_still_add_up_to_the_converted_total() -> None:
    """Three lines rounded on their own are a cent off; the largest takes the cent."""
    lines = [Decimal("3.33"), Decimal("3.33"), Decimal("3.34")]

    total, converted = convert_receipt(Decimal("10.00"), lines, Decimal("0.5"))

    assert total == Decimal("5.00")
    assert sum(converted) == total
    assert converted == [Decimal("1.67"), Decimal("1.67"), Decimal("1.66")]


def test_lines_that_did_not_add_up_are_not_forced_to() -> None:
    total, converted = convert_receipt(
        Decimal("10.00"), [Decimal("3.00"), Decimal("3.00")], Decimal("2")
    )

    assert (total, converted) == (Decimal("20.00"), [Decimal("6.00"), Decimal("6.00")])


@pytest.mark.parametrize(
    ("printed", "expected"),
    [("UAH", "UAH"), ("uah", "UAH"), (None, "PLN"), ("", "PLN"), ("zł", "PLN"), ("PLNX", "PLN")],
)
def test_a_currency_not_read_or_misread_is_the_accounts(printed: Any, expected: str) -> None:
    assert receipt_currency({"currency": printed}, "PLN") == expected


def _ukrainian(**overrides: Any) -> dict[str, Any]:
    return {
        "merchant_name": "Silpo",
        "currency": "UAH",
        "transaction_date": "2026-10-03",
        "receipt_total": "1197.00",
        "computed_total": "1197.00",
        "line_items": [
            {"name": "Kava", "quantity": "1", "unit_price": "397.00", "total_price": "397.00"},
            {"name": "Syr", "quantity": "2", "unit_price": "400.00", "total_price": "800.00"},
        ],
        **overrides,
    }


def test_a_foreign_receipt_is_stored_in_the_accounts_currency_and_keeps_what_was_printed() -> None:
    converted = convert_extraction(_ukrainian(), UAH_PLN)

    assert converted["receipt_total"] == "103.42"
    assert [i["total_price"] for i in converted["line_items"]] == ["34.30", "69.12"]
    assert [i["unit_price"] for i in converted["line_items"]] == ["34.30", "34.56"]
    assert converted["computed_total"] == "103.42"
    assert {k: converted[k] for k in ("currency", "original_currency", "original_total")} == {
        "currency": "PLN",
        "original_currency": "UAH",
        "original_total": "1197.00",
    }
    assert (
        converted["exchange_rate"],
        converted["exchange_rate_date"],
        converted["exchange_rate_source"],
    ) == ("0.0864", "2026-10-02", "NBP")


def test_converting_leaves_the_wizards_copy_untouched() -> None:
    reading = _ukrainian()

    convert_extraction(reading, UAH_PLN)

    assert reading["receipt_total"] == "1197.00"
    assert reading["line_items"][0]["total_price"] == "397.00"


def test_a_line_matched_as_a_repeat_does_not_take_the_rounding_cent() -> None:
    """B2: the repeated line is not stored, so only the counted lines must add up."""
    reading = _ukrainian(
        line_items=[
            {"name": "A", "quantity": "1", "unit_price": "333", "total_price": "333"},
            {"name": "A", "quantity": "1", "unit_price": "333", "total_price": "333"},
            {"name": "B", "quantity": "1", "unit_price": "334", "total_price": "334"},
            {"name": "C", "quantity": "1", "unit_price": "333", "total_price": "333"},
        ],
        receipt_total="1000",
        position_matches=[{"item_a_index": 0, "item_b_index": 1, "result": "same"}],
    )

    converted = convert_extraction(reading, UAH_PLN)

    counted = [converted["line_items"][i]["total_price"] for i in (0, 2, 3)]
    assert sum(Decimal(p) for p in counted) == Decimal(converted["receipt_total"])


def test_the_wizard_is_shown_the_rate_and_the_total_it_gives() -> None:
    assert conversion_preview(_ukrainian(), UAH_PLN) == {
        "currency": "UAH",
        "account_currency": "PLN",
        "rate": "0.0864",
        "rate_date": "2026-10-02",
        "source": "NBP",
        "converted_total": "103.42",
    }


def test_without_a_rate_a_foreign_receipt_is_held_in_review_unconverted() -> None:
    """Never counted as if 1197 UAH were 1197 PLN (A11, D3)."""
    held = unconverted(_ukrainian(conversion={"unavailable": True}), "UAH")

    assert held["receipt_total"] == "1197.00"
    assert held["requires_manual_review"] is True
    assert (held["original_currency"], held["exchange_rate"]) == ("UAH", None)
    assert "conversion" not in held
