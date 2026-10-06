"""Which spending a goal concerns, and how its evidence is written down (BRD F2 — F8.3)."""

import uuid
from dataclasses import replace
from datetime import date
from decimal import Decimal
from typing import Any

from app.domain.goal_analysis import (
    DismissedRecommendation,
    FeedbackState,
    GoalAnalysis,
    GoalBrief,
    RecurringItem,
    analysis_window,
    largest_increases,
    render_advice_context,
    scope_of,
)
from app.domain.goals import FinancialKind, GoalType
from app.domain.periods import DateRange
from app.domain.statistics import CategoryChange, CategoryStanding

SNACKS = uuid.uuid4()


LOSE_WEIGHT = GoalBrief(
    name="Lose weight",
    description=None,
    type=GoalType.LIFESTYLE,
    financial_kind=None,
    target_amount=None,
    category_id=None,
    category_name=None,
    mapped_category_ids=(SNACKS,),
    mapped_item_names=("chocolate",),
)


def _goal(**changes: Any) -> GoalBrief:
    return replace(LOSE_WEIGHT, **changes)


def _standing(name: str, total: str) -> CategoryStanding:
    return CategoryStanding(uuid.uuid4(), name, Decimal(total), Decimal("10.0"), 3)


def _change(name: str, before: str, now: str) -> CategoryChange:
    change = Decimal(now) - Decimal(before)
    percent = (change / Decimal(before) * 100).quantize(Decimal("0.1")) if Decimal(before) else None
    return CategoryChange(_standing(name, now), Decimal(before), change, percent)


def _analysis(goal: GoalBrief, **changes: Any) -> GoalAnalysis:
    empty = GoalAnalysis(
        goal=goal,
        scope=scope_of(goal),
        window=DateRange(date(2026, 7, 1), date(2026, 9, 29)),
        compared_with=DateRange(date(2026, 4, 1), date(2026, 6, 29)),
        receipt_count=14,
        highest_spend=[],
        largest_increases=[],
        goal_categories=[],
        recurring_items=[],
    )
    return replace(empty, **changes)


def test_the_history_read_is_the_running_month_and_the_two_before_it() -> None:
    assert analysis_window(date(2026, 9, 29)) == DateRange(date(2026, 7, 1), date(2026, 9, 29))
    assert analysis_window(date(2026, 1, 15)) == DateRange(date(2025, 11, 1), date(2026, 1, 15))


def test_a_lifestyle_goal_concerns_what_it_watches() -> None:
    scope = scope_of(_goal())
    assert (scope.category_ids, scope.keywords, scope.whole_spend) == (
        (SNACKS,),
        ("chocolate",),
        False,
    )


def test_a_lifestyle_goal_watching_nothing_concerns_nothing() -> None:
    assert scope_of(_goal(mapped_category_ids=(), mapped_item_names=())).is_empty


def test_a_category_reduction_concerns_its_one_category() -> None:
    category = uuid.uuid4()
    goal = _goal(
        type=GoalType.FINANCIAL,
        financial_kind=FinancialKind.CATEGORY_REDUCTION,
        target_amount=Decimal(400),
        category_id=category,
        mapped_category_ids=(),
        mapped_item_names=(),
    )
    assert (scope_of(goal).category_ids, scope_of(goal).whole_spend) == ((category,), False)


def test_a_spending_ceiling_concerns_all_spending() -> None:
    goal = _goal(
        type=GoalType.FINANCIAL,
        financial_kind=FinancialKind.SPENDING_CEILING,
        target_amount=Decimal(3000),
        mapped_category_ids=(),
        mapped_item_names=(),
    )
    assert scope_of(goal).whole_spend


def test_the_largest_increases_are_ranked_by_amount_and_include_new_spending() -> None:
    small_but_steep = _change("Coffee", "1", "10")
    large = _change("Dining", "500", "900")
    new = _change("Gym", "0", "120")
    fell = _change("Transport", "300", "100")

    ranked = largest_increases([small_but_steep, large, new, fell], limit=3)

    assert [c.standing.name for c in ranked] == ["Dining", "Gym", "Coffee"]


def test_the_context_cites_a_recurring_purchase_by_its_shop() -> None:
    """The claim F8.4 must be able to make: "9 of your 14 Fresh Market receipts"."""
    item = RecurringItem("Milka chocolate", 9, Decimal("45.00"), "Fresh Market", 9, 14)

    context = render_advice_context(_analysis(_goal(), recurring_items=[item]), "PLN")

    assert (
        "- Milka chocolate: on 9 receipts, 45.00 PLN in all; "
        "on 9 of the 14 receipts from Fresh Market" in context
    )
    assert "## Recurring purchases related to this goal" in context


def test_the_context_says_so_when_a_section_is_empty_rather_than_leaving_a_gap() -> None:
    context = render_advice_context(_analysis(_goal()), "PLN")

    assert "- none in this period" in context
    assert "- no category grew" in context
    assert "- nothing spent in them in this period" in context
    assert "- no purchase recurs in this period" in context
    assert "History analysed: 1 July 2026 to 29 September 2026, 14 receipts." in context


def test_the_context_states_a_money_goals_target_in_the_users_currency() -> None:
    goal = _goal(
        type=GoalType.FINANCIAL,
        financial_kind=FinancialKind.CATEGORY_REDUCTION,
        target_amount=Decimal(400),
        category_id=uuid.uuid4(),
        category_name="Dining",
        mapped_category_ids=(),
        mapped_item_names=(),
    )

    context = render_advice_context(_analysis(goal), "EUR")

    assert "Target: keep Dining under 400.00 EUR a month" in context


def test_the_context_lists_advice_the_user_turned_down_so_it_is_not_repeated() -> None:
    turned_down = DismissedRecommendation("Dining", "Skip lunch out", FeedbackState.NOT_HELPFUL)

    context = render_advice_context(
        _analysis(_goal(), dismissed_recommendations=[turned_down]), "PLN"
    )

    assert "## Advice the user turned down" in context
    assert "- Dining: Skip lunch out (not helpful)" in context


def test_the_context_leaves_out_the_turned_down_section_when_there_is_none() -> None:
    assert "turned down" not in render_advice_context(_analysis(_goal()), "PLN")
