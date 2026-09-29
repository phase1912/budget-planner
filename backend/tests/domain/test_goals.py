"""What makes a goal well formed (BRD F1, F9)."""

import uuid
from decimal import Decimal

import pytest

from app.domain.goals import (
    WATCHED_ITEM_MAX_LENGTH,
    WATCHED_LINES_MAX,
    FinancialKind,
    GoalShape,
    GoalType,
    InvalidGoal,
    check_goal,
    clean_item_names,
)

CATEGORY = uuid.uuid4()


@pytest.mark.parametrize(
    "shape",
    [
        GoalShape(GoalType.FINANCIAL, FinancialKind.SPENDING_CEILING, Decimal(3000), None),
        GoalShape(GoalType.FINANCIAL, FinancialKind.SAVINGS_TARGET, Decimal(500), None),
        GoalShape(GoalType.FINANCIAL, FinancialKind.CATEGORY_REDUCTION, Decimal(400), CATEGORY),
        GoalShape(GoalType.LIFESTYLE, None, None, None),
        GoalShape(GoalType.LIFESTYLE, None, None, None, watches_spending=True),
    ],
)
def test_each_kind_of_goal_is_accepted_in_its_own_shape(shape: GoalShape) -> None:
    check_goal(shape)


@pytest.mark.parametrize(
    ("shape", "reason"),
    [
        (GoalShape(GoalType.FINANCIAL, None, Decimal(3000), None), "kind of money goal"),
        (GoalShape(GoalType.FINANCIAL, FinancialKind.SAVINGS_TARGET, None, None), "above zero"),
        (
            GoalShape(GoalType.FINANCIAL, FinancialKind.SAVINGS_TARGET, Decimal(0), None),
            "above zero",
        ),
        (
            GoalShape(GoalType.FINANCIAL, FinancialKind.CATEGORY_REDUCTION, Decimal(400), None),
            "category to cut",
        ),
        (
            GoalShape(GoalType.FINANCIAL, FinancialKind.SPENDING_CEILING, Decimal(9), CATEGORY),
            "Only a goal cutting",
        ),
        (GoalShape(GoalType.LIFESTYLE, None, Decimal(10), None), "lifestyle goal has no"),
        (GoalShape(GoalType.LIFESTYLE, FinancialKind.SAVINGS_TARGET, None, None), "no amount"),
        (
            GoalShape(
                GoalType.FINANCIAL,
                FinancialKind.SPENDING_CEILING,
                Decimal(9),
                None,
                watches_spending=True,
            ),
            "Only a lifestyle goal watches",
        ),
    ],
)
def test_a_goal_whose_parts_do_not_fit_its_type_is_refused_with_the_reason(
    shape: GoalShape, reason: str
) -> None:
    with pytest.raises(InvalidGoal, match=reason):
        check_goal(shape)


def test_watched_item_names_are_tidied_blanks_and_repeats_dropped_order_kept() -> None:
    assert clean_item_names(["  Sweets ", "", "beer", "SWEETS", "   "]) == ["sweets", "beer"]


def test_watched_item_names_are_cut_to_what_the_column_holds() -> None:
    names = ["x" * 500] + [f"item {n}" for n in range(WATCHED_LINES_MAX + 5)]

    cleaned = clean_item_names(names)

    assert len(cleaned[0]) == WATCHED_ITEM_MAX_LENGTH
    assert len(cleaned) == WATCHED_LINES_MAX
