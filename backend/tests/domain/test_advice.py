"""Advice must name what the receipts show; anything else is generic (BRD F3, 11.3)."""

import uuid
from dataclasses import replace
from datetime import date
from decimal import Decimal

from app.domain.advice import (
    ADVICE_MAX,
    Advice,
    AdviceTarget,
    ProjectedImpact,
    assess_readiness,
    keep_specific,
    project_impact,
)
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


def _advice(
    kind: AdviceTarget, target: str, action: str = "Stop buying it", percent: int = 100
) -> Advice:
    return Advice(kind, target, action, "Seen on 9 of 14 receipts.", percent)


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


def test_advice_removing_nothing_is_dropped_and_more_than_everything_is_capped() -> None:
    proposed = [
        _advice(AdviceTarget.CATEGORY, "Dining", percent=0),
        _advice(AdviceTarget.ITEM, "Cookies Choco 300g", percent=150),
    ]

    assert [a.reduction_percent for a in keep_specific(proposed, ANALYSIS)] == [100]


# ANALYSIS covers 1 July to 29 September 2026: 91 days, 2.9897 average months.


def test_stopping_a_recurring_purchase_saves_its_monthly_spend_and_its_purchases() -> None:
    """61.20 over the window and 9 receipts: 20.47 a month, 3.0 purchases a month."""
    impact = project_impact(_advice(AdviceTarget.ITEM, "Cookies Choco 300g"), ANALYSIS)

    assert impact == ProjectedImpact(Decimal("20.47"), Decimal("3.0"))


def test_halving_saves_half_and_a_category_has_no_purchase_count() -> None:
    impact = project_impact(_advice(AdviceTarget.CATEGORY, "dining", percent=50), ANALYSIS)

    assert impact == ProjectedImpact(Decimal("50.17"), None)


def test_a_target_refunded_more_than_it_cost_saves_nothing() -> None:
    refunded = replace(
        ANALYSIS,
        highest_spend=[CategoryStanding(uuid.uuid4(), "Dining", Decimal(-40), Decimal(0), 1)],
    )

    impact = project_impact(_advice(AdviceTarget.CATEGORY, "Dining"), refunded)

    assert impact.monthly_saving == Decimal("0.00")


def test_advice_needs_both_enough_receipts_and_a_month_of_history() -> None:
    """BRD F5: a pile of receipts from one afternoon is not a pattern, nor is a sparse month."""
    today = date(2026, 10, 7)

    def ready(receipts: int, first: date | None) -> bool:
        return assess_readiness(receipts, first, today, required_receipts=4, required_days=30).ready

    assert ready(4, date(2026, 9, 7))
    assert not ready(20, date(2026, 10, 7))
    assert not ready(3, date(2026, 6, 1))
    assert not ready(0, None)


def test_readiness_progress_follows_the_slower_minimum() -> None:
    today = date(2026, 10, 7)

    receipts_short = assess_readiness(
        1, date(2026, 8, 1), today, required_receipts=4, required_days=30
    )
    days_short = assess_readiness(
        10, date(2026, 9, 28), today, required_receipts=4, required_days=30
    )

    assert (receipts_short.progress, days_short.progress) == (25, 30)
