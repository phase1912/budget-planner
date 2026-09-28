"""What makes a goal well formed (BRD F1).

One rule set for creating a goal and for changing one, so an edit can never leave a
goal in a state creating it would have refused.
"""

import enum
import uuid
from dataclasses import dataclass
from decimal import Decimal


class GoalType(enum.StrEnum):
    """The distinction BRD F9 depends on: a money target, or a way of living (F1)."""

    FINANCIAL = "financial"
    LIFESTYLE = "lifestyle"


class FinancialKind(enum.StrEnum):
    """The three money targets BRD F1 names; a lifestyle goal has none.

    `spending_ceiling` keeps a month's spend under `target_amount`; `savings_target`
    puts `target_amount` aside; `category_reduction` keeps one category, the goal's
    `category_id`, under `target_amount` a month.
    """

    SPENDING_CEILING = "spending_ceiling"
    SAVINGS_TARGET = "savings_target"
    CATEGORY_REDUCTION = "category_reduction"


class InvalidGoal(ValueError):
    """A goal whose fields contradict each other; the message says which, for the user."""


@dataclass(frozen=True)
class GoalShape:
    """The fields that must agree with each other, whatever else a goal holds."""

    type: GoalType
    financial_kind: FinancialKind | None
    target_amount: Decimal | None
    category_id: uuid.UUID | None


def check_goal(goal: GoalShape) -> None:
    """Refuse a goal whose parts do not fit its type (BRD F1, F9).

    A financial goal names its kind and a positive amount, and a category exactly
    when it cuts one. A lifestyle goal has none of these: it is read through the
    things bought, not a sum, and keeping the two apart is what F9 relies on.

    Raises InvalidGoal with a message fit to show.
    """
    if goal.type is GoalType.LIFESTYLE:
        if goal.financial_kind or goal.target_amount is not None or goal.category_id:
            raise InvalidGoal("A lifestyle goal has no amount, kind or category.")
        return
    if goal.financial_kind is None:
        raise InvalidGoal("Say what kind of money goal this is.")
    if goal.target_amount is None or goal.target_amount <= 0:
        raise InvalidGoal("A money goal needs an amount above zero.")
    cuts_a_category = goal.financial_kind is FinancialKind.CATEGORY_REDUCTION
    if cuts_a_category and goal.category_id is None:
        raise InvalidGoal("Pick the category to cut.")
    if not cuts_a_category and goal.category_id is not None:
        raise InvalidGoal("Only a goal cutting one category names a category.")
