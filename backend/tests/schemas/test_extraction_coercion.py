"""Vision models answer with bare numbers where the schema asks for strings.

Rejecting those costs a whole receipt over JSON's number/string distinction,
so the extraction schemas coerce instead (BRD A9).
"""

from decimal import Decimal

import pytest

from app.schemas.extraction import ExtractedLineItem, ExtractedReceipt, normalise_amount


def test_numeric_quantity_from_the_model_is_accepted() -> None:
    # Given a model that answered "quantity": 1 rather than "1"
    item = ExtractedLineItem.model_validate(
        {"name": "MILKA", "quantity": 1, "unit_price": 7.49, "total_price": 7.49}
    )

    # Then
    assert item.quantity == "1"
    assert item.unit_price == "7.49"


def test_numeric_receipt_total_is_accepted() -> None:
    # Given
    receipt = ExtractedReceipt.model_validate({"receipt_total": 78.45, "line_items": []})

    # Then
    assert receipt.receipt_total == "78.45"


@pytest.mark.parametrize(
    ("printed", "expected"),
    [
        ("7,49A", "7,49"),
        ("13,99C", "13,99"),
        ("2.19B", "2.19"),
        ("10szt", "10"),
        ("1 szt.", "1"),
        ("4,39", "4,39"),
        ("C", ""),
        ("", ""),
    ],
)
def test_printed_tax_class_and_units_are_stripped(printed: str, expected: str) -> None:
    assert normalise_amount(printed) == expected


def test_line_item_price_survives_the_vat_class_letter() -> None:
    # Given the shape a Polish receipt actually produces
    item = ExtractedLineItem.model_validate(
        {"name": "MILKA", "quantity": "1szt", "unit_price": "7,49", "total_price": "7,49A"}
    )

    # Then it converts instead of falling back to zero
    assert Decimal(item.total_price.replace(",", ".")) == Decimal("7.49")
    assert item.quantity == "1"


def test_line_with_no_price_at_all_is_reported_missing_not_zero() -> None:
    # Given a line the model read as the tax class alone
    item = ExtractedLineItem.model_validate(
        {"name": "AGRO-FARM Jaja", "quantity": "10", "unit_price": "C", "total_price": "C"}
    )

    # Then
    assert item.total_price == ""


def test_receipt_arithmetic_works_once_prices_are_normalised() -> None:
    # Given
    receipt = ExtractedReceipt.model_validate(
        {
            "receipt_total": "10,68B",
            "line_items": [
                {"name": "A", "quantity": "1", "unit_price": "7,49", "total_price": "7,49A"},
                {"name": "B", "quantity": "1", "unit_price": "3,19", "total_price": "3,19C"},
            ],
        }
    )

    # Then
    assert receipt.receipt_total == "10,68"
    assert receipt.items_sum_matches_total is True
