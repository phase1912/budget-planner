"""Reading a receipt's fiscal identity off what the model returned (F11.3, ADR-0015)."""

import pytest

from app.domain.fiscal_identity import fiscal_identity, is_left_out, normalise


@pytest.mark.parametrize(
    ("printed", "expected"),
    [
        ("ECA 2201079960", "ECA2201079960"),
        ("nr:85503", "85503"),
        ("Nr. 85503", "85503"),
        ("ФН 3000898168", "3000898168"),
        ("eca-2201079960", "ECA2201079960"),
        (85503, "85503"),
    ],
)
def test_printed_numbers_are_reduced_to_letters_and_digits(printed: object, expected: str) -> None:
    assert normalise(printed) == expected


@pytest.mark.parametrize("printed", [None, "", "   ", "nr:", "PARAGON FISKALNY"])
def test_text_without_a_number_is_no_fiscal_number(printed: object) -> None:
    assert normalise(printed) is None


def test_a_receipt_is_identified_by_its_register_and_its_number_together() -> None:
    extraction = {"fiscal_register_id": "ECA 2201079960", "fiscal_receipt_number": "nr:85503"}

    assert fiscal_identity(extraction) == ("ECA2201079960", "85503")


@pytest.mark.parametrize(
    "extraction",
    [
        {"fiscal_register_id": "ECA 2201079960", "fiscal_receipt_number": None},
        {"fiscal_register_id": None, "fiscal_receipt_number": "85503"},
        {"fiscal_register_id": "12", "fiscal_receipt_number": "85503"},
        {},
    ],
)
def test_half_an_identity_or_a_misread_register_identifies_nothing(
    extraction: dict[str, object],
) -> None:
    assert fiscal_identity(extraction) is None


@pytest.mark.parametrize(
    ("extraction", "left_out"),
    [
        ({"already_stored": {"receipt_id": "x"}}, True),
        ({"is_skipped": True}, True),
        ({"duplicate_resolved": "skipped"}, True),
        ({"duplicate_resolved": "skip"}, True),
        ({"duplicate_resolved": "stored"}, False),
        ({}, False),
    ],
)
def test_a_receipt_already_stored_or_skipped_is_left_out_of_storing(
    extraction: dict[str, object], left_out: bool
) -> None:
    assert is_left_out(extraction) is left_out
