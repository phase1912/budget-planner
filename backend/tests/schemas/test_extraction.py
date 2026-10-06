from app.schemas.extraction import ExtractedLineItem, ExtractedReceipt


def test_receipt_arithmetic_matches() -> None:
    receipt = ExtractedReceipt(
        merchant_name="Test Store",
        merchant_name_confidence=1.0,
        transaction_date="2026-08-18",
        transaction_date_confidence=1.0,
        transaction_time="14:30",
        transaction_time_confidence=1.0,
        currency="PLN",
        line_items=[
            ExtractedLineItem(name="Item 1", quantity="1", unit_price="10.00", total_price="10.00"),
            ExtractedLineItem(name="Item 2", quantity="2", unit_price="5.50", total_price="11.00"),
        ],
        receipt_total="21.00",
        receipt_total_confidence=1.0,
    )
    assert receipt.items_sum_matches_total is True
    assert receipt.computed_total == "21.00"


def test_receipt_arithmetic_mismatches() -> None:
    receipt = ExtractedReceipt(
        merchant_name="Test Store",
        merchant_name_confidence=1.0,
        currency="PLN",
        line_items=[
            ExtractedLineItem(name="Item 1", quantity="1", unit_price="10.00", total_price="10.00"),
        ],
        receipt_total="11.00",
        receipt_total_confidence=1.0,
    )
    assert receipt.items_sum_matches_total is False
    assert receipt.computed_total == "10.00"


def test_receipt_arithmetic_missing_total() -> None:
    receipt = ExtractedReceipt(
        merchant_name="Test Store",
        merchant_name_confidence=1.0,
        currency="PLN",
        line_items=[
            ExtractedLineItem(name="Item 1", quantity="1", unit_price="10.00", total_price="10.00"),
        ],
        receipt_total=None,
        receipt_total_confidence=1.0,
    )
    assert receipt.items_sum_matches_total is None
    assert receipt.computed_total == "10.00"


def test_receipt_arithmetic_empty_lines() -> None:
    receipt = ExtractedReceipt(
        merchant_name="Test Store",
        merchant_name_confidence=1.0,
        currency="PLN",
        line_items=[],
        receipt_total="10.00",
        receipt_total_confidence=1.0,
    )
    assert receipt.items_sum_matches_total is None
    assert receipt.computed_total is None


def test_receipt_arithmetic_missing_line_price() -> None:
    receipt = ExtractedReceipt(
        merchant_name="Test Store",
        merchant_name_confidence=1.0,
        currency="PLN",
        line_items=[
            ExtractedLineItem(name="Item 1", quantity="1", unit_price="10.00", total_price=""),
        ],
        receipt_total="10.00",
        receipt_total_confidence=1.0,
    )
    assert receipt.items_sum_matches_total is None
    assert receipt.computed_total is None


def test_receipt_arithmetic_invalid_decimal() -> None:
    receipt = ExtractedReceipt(
        merchant_name="Test Store",
        merchant_name_confidence=1.0,
        currency="PLN",
        line_items=[
            ExtractedLineItem(
                name="Item 1",
                quantity="1",
                unit_price="10.00",
                total_price="invalid",
            ),
        ],
        receipt_total="10.00",
        receipt_total_confidence=1.0,
    )
    assert receipt.items_sum_matches_total is None
    assert receipt.computed_total is None


def test_receipt_requires_manual_review_when_total_missing() -> None:
    receipt = ExtractedReceipt(
        transaction_date="2026-08-18",
        line_items=[],
        receipt_total=None,
    )
    assert receipt.requires_manual_review is True


def test_receipt_requires_manual_review_when_date_missing() -> None:
    receipt = ExtractedReceipt(
        transaction_date=None,
        line_items=[],
        receipt_total="10.00",
    )
    assert receipt.requires_manual_review is True


def test_receipt_no_manual_review_when_both_present() -> None:
    receipt = ExtractedReceipt(
        transaction_date="2026-08-18",
        line_items=[],
        receipt_total="10.00",
    )
    assert receipt.requires_manual_review is False


def _biedronka(*lines: tuple[str, str], total: str) -> ExtractedReceipt:
    return ExtractedReceipt(
        merchant_name="Biedronka",
        transaction_date="2026-10-05",
        currency="PLN",
        line_items=[
            ExtractedLineItem(name=name, quantity="1", unit_price=price, total_price=price)
            for name, price in lines
        ],
        receipt_total=total,
    )


def test_a_discount_line_brings_the_lines_down_to_what_was_paid() -> None:
    """The case that held a real receipt out of the month: discounts read, total agrees."""
    receipt = _biedronka(("Masło 200g", "17,97"), ("Rabat", "-6,00"), total="11,97")

    assert receipt.items_sum_matches_total is True


def test_a_minus_printed_after_the_amount_still_counts_as_a_discount() -> None:
    receipt = _biedronka(("Masło 200g", "17,97A"), ("OPUST", "6,00-"), total="11,97")

    assert receipt.line_items[1].total_price == "-6,00"
    assert receipt.items_sum_matches_total is True


def test_a_grosz_of_rounding_is_not_a_mismatch_but_more_is() -> None:
    assert _biedronka(("Łosoś kg", "118.97"), total="118.98").items_sum_matches_total is True
    assert _biedronka(("Łosoś kg", "118.97"), total="119.00").items_sum_matches_total is False
