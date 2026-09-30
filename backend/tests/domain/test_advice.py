"""Advice must name what the receipts show; anything else is generic (BRD F3, 11.3)."""

import uuid
from dataclasses import replace
from datetime import date
from decimal import Decimal

from app.domain.advice import ADVICE_MAX, Advice, AdviceTarget, keep_specific
from app.domain.goal_analysis import GoalAnalysis, GoalBrief, RecurringItem, scope_of
from app.domain.goals import GoalType
from app.domain.periods import DateRange
from app.domain.statistics import CategoryStanding

GOAL = GoalBrief(
    name="Lose weight",
    description=None,
    type=GoalType.LIFESTYLE,
    financial_kind=None,
    target_amount=None,
    category_id=None,
    category_name=None,
    mapped_category_ids=(),
    mapped_item_names=("cookies",),
)
ANALYSIS = GoalAnalysis(
    goal=GOAL,
    scope=scope_of(GOAL),
    window=DateRange(date(2026, 7, 1), date(2026, 9, 29)),
    compared_with=DateRange(date(2026, 4, 1), date(2026, 6, 29)),
    receipt_count=14,
    highest_spend=[CategoryStanding(uuid.uuid4(), "Dining", Decimal(300), Decimal(30), 6)],
    largest_increases=[],
    goal_categories=[],
    recurring_items=[
        RecurringItem("Cookies Choco 300g", 9, Decimal("61.20"), "Fresh Market", 9, 14)
    ],
)


def _advice(kind: AdviceTarget, target: str, action: str = "Stop buying it") -> Advice:
    return Advice(kind, target, action, "Seen on 9 of 14 receipts.")


def test_advice_naming_a_purchase_or_category_from_the_receipts_is_kept() -> None:
    proposed = [
        _advice(AdviceTarget.ITEM, "cookies choco 300g "),
        _advice(AdviceTarget.CATEGORY, "Dining", "Cap dining at 200 PLN"),
    ]

    kept = keep_specific(proposed, ANALYSIS)

    assert [(a.target_kind, a.target_name) for a in kept] == [
        (AdviceTarget.ITEM, "cookies choco 300g"),
        (AdviceTarget.CATEGORY, "Dining"),
    ]


def test_generic_advice_naming_nothing_from_the_receipts_is_refused() -> None:
    proposed = [
        _advice(AdviceTarget.CATEGORY, "Discretionary spending", "Consider reducing it"),
        _advice(AdviceTarget.ITEM, "Snacks", "Buy fewer snacks"),
        _advice(AdviceTarget.ITEM, "Dining"),
    ]

    assert keep_specific(proposed, ANALYSIS) == []


def test_one_target_is_advised_on_once_and_an_empty_action_is_dropped() -> None:
    proposed = [
        _advice(AdviceTarget.ITEM, "Cookies Choco 300g", "  "),
        _advice(AdviceTarget.ITEM, "Cookies Choco 300g"),
        _advice(AdviceTarget.ITEM, "COOKIES CHOCO 300G", "Halve it"),
    ]

    assert [a.action for a in keep_specific(proposed, ANALYSIS)] == ["Stop buying it"]


def test_no_more_than_the_limit_is_kept() -> None:
    names = [f"Item {n}" for n in range(ADVICE_MAX + 2)]
    analysis = replace(
        ANALYSIS, recurring_items=[RecurringItem(n, 2, Decimal(5), None, 0, 0) for n in names]
    )

    kept = keep_specific([_advice(AdviceTarget.ITEM, n) for n in names], analysis)

    assert [a.target_name for a in kept] == names[:ADVICE_MAX]
