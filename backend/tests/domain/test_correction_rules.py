"""Which correction rule, if any, files a new item (BRD C5, ADR-0008)."""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.domain.categories import match_rule, normalise_name

HEALTH, SNACKS, DRINKS = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()


@dataclass
class Rule:
    merchant_name: str
    item_name: str
    category_id: uuid.UUID
    created_at: datetime = field(default_factory=lambda: datetime(2026, 7, 1, tzinfo=UTC))


def rule(item: str, category: uuid.UUID, merchant: str = "Fresh Market", **kw: datetime) -> Rule:
    return Rule(normalise_name(merchant), normalise_name(item), category, **kw)


def test_same_name_from_the_same_merchant_is_filed_by_the_rule() -> None:
    assert match_rule("Protein Bar XL", "Fresh Market", [rule("Protein Bar XL", HEALTH)]) == HEALTH


def test_case_spacing_and_small_ocr_noise_still_match() -> None:
    rules = [rule("Protein Bar XL", HEALTH)]
    assert match_rule("  PROTEIN  bar xl ", "fresh market", rules) == HEALTH
    assert match_rule("Protein Bar XL.", "Fresh Market", rules) == HEALTH


def test_a_rule_never_crosses_to_another_merchant() -> None:
    assert match_rule("Protein Bar XL", "Corner Shop", [rule("Protein Bar XL", HEALTH)]) is None


def test_an_unrelated_item_from_the_same_merchant_is_left_to_the_agent() -> None:
    assert (
        match_rule("Sparkling water 1.5L", "Fresh Market", [rule("Protein Bar XL", HEALTH)]) is None
    )


def test_an_exact_name_beats_a_merely_similar_one() -> None:
    rules = [rule("Protein Bar XXL", SNACKS), rule("Protein Bar XL", HEALTH)]
    assert match_rule("Protein Bar XL", "Fresh Market", rules) == HEALTH


def test_on_a_tie_the_users_latest_word_wins() -> None:
    older = rule("Cola", DRINKS, created_at=datetime(2026, 7, 1, tzinfo=UTC))
    newer = rule("Cola", SNACKS, created_at=datetime(2026, 7, 9, tzinfo=UTC))
    assert match_rule("Cola", "Fresh Market", [newer, older]) == SNACKS
    assert match_rule("Cola", "Fresh Market", [older, newer]) == SNACKS


def test_a_receipt_with_no_merchant_only_matches_rules_made_without_one() -> None:
    assert match_rule("Cola", None, [rule("Cola", DRINKS, merchant="")]) == DRINKS
    assert match_rule("Cola", None, [rule("Cola", DRINKS)]) is None
