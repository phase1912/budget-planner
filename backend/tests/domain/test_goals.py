"""What makes a goal well formed (BRD F1, F9)."""

import uuid
from decimal import Decimal

import pytest

from app.domain.goals import FinancialKind, GoalShape, GoalType, InvalidGoal, check_goal

CATEGORY = uuid.uuid4()


@pytest.mark.parametrize(
    "shape",
    [
        GoalShape(GoalType.FINANCIAL, FinancialKind.SPENDING_CEILING, Decimal(3000), None),
        GoalShape(GoalType.FINANCIAL, FinancialKind.SAVINGS_TARGET, Decimal(500), None),
        GoalShape(GoalType.FINANCIAL, FinancialKind.CATEGORY_REDUCTION, Decimal(400), CATEGORY),
        GoalShape(GoalType.LIFESTYLE, None, None, None),
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
    ],
)
def test_a_goal_whose_parts_do_not_fit_its_type_is_refused_with_the_reason(
    shape: GoalShape, reason: str
) -> None:
    with pytest.raises(InvalidGoal, match=reason):
        check_goal(shape)
