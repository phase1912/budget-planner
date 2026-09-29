"""What makes a goal well formed (BRD F1).

One rule set for creating a goal and for changing one, so an edit can never leave a
goal in a state creating it would have refused.
"""

import enum
import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal

WATCHED_ITEM_MAX_LENGTH = 120
"""The longest spending line a lifestyle goal can watch, as the column stores it."""

WATCHED_LINES_MAX = 20
"""How many categories, and how many item names, one lifestyle goal can watch."""


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
    watches_spending: bool = False


def check_goal(goal: GoalShape) -> None:
    """Refuse a goal whose parts do not fit its type (BRD F1, F9).

    A financial goal names its kind and a positive amount, and a category exactly
    when it cuts one. A lifestyle goal has none of these: it is read through the
    things bought, not a sum, and keeping the two apart is what F9 relies on. Only
    a lifestyle goal watches spending lines; a money goal already knows what it limits.

    Raises InvalidGoal with a message fit to show.
    """
    if goal.type is GoalType.LIFESTYLE:
        if goal.financial_kind or goal.target_amount is not None or goal.category_id:
            raise InvalidGoal("A lifestyle goal has no amount, kind or category.")
        return
    if goal.financial_kind is None:
        raise InvalidGoal("Say what kind of money goal this is.")
    if goal.watches_spending:
        raise InvalidGoal("Only a lifestyle goal watches spending lines.")
    if goal.target_amount is None or goal.target_amount <= 0:
        raise InvalidGoal("A money goal needs an amount above zero.")
    cuts_a_category = goal.financial_kind is FinancialKind.CATEGORY_REDUCTION
    if cuts_a_category and goal.category_id is None:
        raise InvalidGoal("Pick the category to cut.")
    if not cuts_a_category and goal.category_id is not None:
        raise InvalidGoal("Only a goal cutting one category names a category.")


def clean_item_names(names: Iterable[str]) -> list[str]:
    """The item names a lifestyle goal watches, tidied for storage (BRD F9 — F8.2).

    Trimmed, lower-cased, cut to the column's length, blanks and repeats dropped,
    order kept, at most WATCHED_LINES_MAX. Used on the model's answer, which is
    never trusted to be tidy, and on the user's own list alike.
    """
    cleaned: list[str] = []
    for name in names:
        item = name.strip().lower()[:WATCHED_ITEM_MAX_LENGTH].strip()
        if item and item not in cleaned:
            cleaned.append(item)
    return cleaned[:WATCHED_LINES_MAX]
