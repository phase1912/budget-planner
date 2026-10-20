"""The reading score counts a line right only when its amount and name both match (F15.5.4)."""

from typing import Any

from scripts.evaluate_reading import score

EXPECTED: dict[str, Any] = {
    "receipt_total": "952.00",
    "line_items": [
        {"name": "Біг Мак Меню", "total_price": "299.00"},
        {"name": "Велика картопля", "total_price": "15.00"},
        {"name": "Знижка", "total_price": "-14.95"},
    ],
}


def test_a_folded_add_on_and_an_invented_line_both_count_against_the_reading() -> None:
    read = {
        "receipt_total": "299.05",
        "line_items": [
            {"name": "Біг Мак Меню", "total_price": "314.00"},
            {"name": "Знижка", "total_price": "-14.95"},
            {"name": "Кока-кола", "total_price": "0.00"},
        ],
    }

    result = score("mcd", EXPECTED, read, 1.0)

    assert (result.found, result.expected, result.extra) == (1, 3, 2)
    assert not result.total_right


def test_a_right_reading_scores_every_line_and_adds_up() -> None:
    read = {**EXPECTED, "line_items": [dict(line) for line in EXPECTED["line_items"]]}
    read["receipt_total"] = "299.05"

    result = score("mcd", {**EXPECTED, "receipt_total": "299.05"}, read, 1.0)

    assert (result.found, result.extra, result.total_right, result.adds_up) == (3, 0, True, True)
