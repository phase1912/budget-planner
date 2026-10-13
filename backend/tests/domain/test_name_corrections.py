"""A misreading fixed once stays fixed for that shop (F15.3)."""

from dataclasses import dataclass
from typing import Any

from app.domain.name_corrections import apply_corrections, printed_name


@dataclass
class Correction:
    merchant_name: str
    read_name: str
    corrected_name: str


BUTTER = Correction("biedronka", "mastozpolskmlecz200g", "Masło 200g")


def _receipt(merchant: str | None, *names: str) -> dict[str, Any]:
    return {"merchant_name": merchant, "line_items": [{"name": n} for n in names]}


def test_the_shops_next_receipt_reads_the_corrected_name_and_keeps_the_printed_one() -> None:
    receipt = _receipt("BIEDRONKA", "MastoZPolskMlecz200g", "Chleb")

    assert apply_corrections(receipt, [BUTTER]) == 1

    assert receipt["line_items"] == [
        {"name": "Masło 200g", "read_name": "MastoZPolskMlecz200g"},
        {"name": "Chleb"},
    ]


def test_another_shops_receipt_is_left_as_printed() -> None:
    receipt = _receipt("Lidl", "MastoZPolskMlecz200g")

    assert apply_corrections(receipt, [BUTTER]) == 0
    assert receipt["line_items"] == [{"name": "MastoZPolskMlecz200g"}]


def test_a_receipt_with_no_merchant_is_never_corrected() -> None:
    receipt = _receipt(None, "MastoZPolskMlecz200g")

    assert apply_corrections(receipt, [BUTTER]) == 0


def test_only_the_same_printed_name_is_corrected_not_a_similar_one() -> None:
    """A near match could be a different product; renaming it would be a silent error."""
    receipt = _receipt("Biedronka", "MastoZPolskMlecz400g")

    assert apply_corrections(receipt, [BUTTER]) == 0


def test_what_was_printed_is_the_read_name_once_corrected() -> None:
    assert printed_name({"name": "Masło 200g", "read_name": "Masto"}, "Masło 200g") == "Masto"
    assert printed_name({"name": "Chleb"}, "Chleb") == "Chleb"
