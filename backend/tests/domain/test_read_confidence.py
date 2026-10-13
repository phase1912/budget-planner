"""Which read lines need the user's look (BRD A10 — F15.2)."""

import pytest

from app.domain.read_confidence import is_doubtful, read_confidence


@pytest.mark.parametrize(
    ("confidence", "doubtful"),
    [(79, True), (80, False), (100, False), (0, True), (None, False)],
)
def test_a_line_is_doubtful_only_below_the_threshold(
    confidence: int | None, doubtful: bool
) -> None:
    """ADR-0005's 0.80: a line read at 80 stands; one with no score is never marked."""
    assert is_doubtful(confidence, 0.80) is doubtful


@pytest.mark.parametrize(
    ("item", "score"),
    [
        ({"confidence": 62}, 62),
        ({"confidence": 140}, 100),
        ({"confidence": "high"}, None),
        ({"confidence": True}, None),
        ({}, None),
    ],
)
def test_only_a_usable_score_is_kept_from_a_reading(
    item: dict[str, object], score: int | None
) -> None:
    assert read_confidence(item) == score
