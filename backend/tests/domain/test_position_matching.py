from dataclasses import dataclass

import pytest

from app.domain.position_matching import ComparisonNotPossible, MatchResult, match_positions


@dataclass
class DummyPosition:
    name: str
    unit_price: str
    quantity: str
    total_price: str


def test_match_positions_same_receipt() -> None:
    a = DummyPosition("Bananas", "3.20", "1", "3.20")
    b = DummyPosition("Bananas", "3.20", "1", "3.20")
    assert match_positions(a, b, same_receipt=True) == MatchResult.SAME


def test_match_positions_different_receipt() -> None:
    a = DummyPosition("Bananas", "3.20", "1", "3.20")
    b = DummyPosition("Bananas", "3.20", "1", "3.20")
    assert match_positions(a, b, same_receipt=False) == MatchResult.DIFFERENT


def test_match_positions_diff_fields() -> None:
    a = DummyPosition("Bananas", "3.20", "1", "3.20")
    b = DummyPosition("Bananas", "3.50", "1", "3.50")
    assert match_positions(a, b, same_receipt=True) == MatchResult.DIFFERENT


def test_match_positions_missing_fields() -> None:
    a = DummyPosition("Bananas", "", "1", "3.20")
    b = DummyPosition("Bananas", "3.20", "1", "3.20")
    with pytest.raises(ComparisonNotPossible):
        match_positions(a, b, same_receipt=True)
