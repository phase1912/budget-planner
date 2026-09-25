"""The total a user types for an unreadable receipt (BRD A11)."""

import pytest
from pydantic import ValidationError

from app.schemas.receipt import ResolveTotalRequest


@pytest.mark.parametrize(
    ("typed", "stored"),
    [("37,00", "37.00"), ("37.5", "37.50"), (" 1 214,60 ", "1214.60"), ("0", "0.00")],
)
def test_a_typed_total_is_stored_in_one_format_whatever_the_decimal_mark(
    typed: str, stored: str
) -> None:
    assert ResolveTotalRequest(extraction_index=0, receipt_total=typed).receipt_total == stored


@pytest.mark.parametrize("typed", ["", "abc", "-5", "NaN", "Infinity"])
def test_a_total_that_is_not_a_non_negative_amount_is_refused_before_it_is_saved(
    typed: str,
) -> None:
    with pytest.raises(ValidationError):
        ResolveTotalRequest(extraction_index=0, receipt_total=typed)
