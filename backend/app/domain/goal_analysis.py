"""The evidence advice on a goal is built from (BRD F2 — F8.3).

Which part of the user's spending a goal concerns, what in it stands out, and how
that is written down for the advice model. Every figure here comes from the user's
own receipts, so a recommendation can cite it rather than invent it (F3, 11.3).
"""

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from app.domain.goals import FinancialKind, GoalType
from app.domain.periods import DateRange
from app.domain.statistics import CategoryChange, CategoryStanding

ANALYSIS_MONTHS = 3
"""How much history is read: the running month and the two before it."""

TOP_CATEGORIES = 3
TOP_INCREASES = 3
RECURRING_ITEMS_MAX = 10
RECURRING_MIN_RECEIPTS = 2
"""A purchase is recurring once it appears on at least this many receipts."""


def analysis_window(as_of: date) -> DateRange:
    """The history read for advice: from the 1st, ANALYSIS_MONTHS back, to `as_of`.

    Starting on a 1st keeps its comparison like for like: the same days of the
    months before (BRD D4, E3).
    """
    first = as_of.replace(day=1)
    for _ in range(ANALYSIS_MONTHS - 1):
        first = (first - timedelta(days=1)).replace(day=1)
    return DateRange(first, as_of)


@dataclass(frozen=True)
class GoalBrief:
    """What the analysis needs to know about a goal, free of the database row."""

    name: str
    description: str | None
    type: GoalType
    financial_kind: FinancialKind | None
    target_amount: Decimal | None
    category_id: uuid.UUID | None
    category_name: str | None
    mapped_category_ids: tuple[uuid.UUID, ...]
    mapped_item_names: tuple[str, ...]


@dataclass(frozen=True)
class GoalScope:
    """The part of the user's spending a goal concerns (BRD F2, F9).

    A lifestyle goal concerns the categories and item keywords it watches; a
    category reduction, its one category; a spending ceiling or savings target,
    everything (`whole_spend`). A lifestyle goal watching nothing concerns nothing.
    """

    category_ids: tuple[uuid.UUID, ...]
    keywords: tuple[str, ...]
    whole_spend: bool

    @property
    def is_empty(self) -> bool:
        """Nothing to look at: no categories, no keywords, and not all spending."""
        return not (self.category_ids or self.keywords or self.whole_spend)


def scope_of(goal: GoalBrief) -> GoalScope:
    """The spending a goal concerns; see GoalScope."""
    if goal.type is GoalType.LIFESTYLE:
        return GoalScope(goal.mapped_category_ids, goal.mapped_item_names, whole_spend=False)
    if goal.financial_kind is FinancialKind.CATEGORY_REDUCTION and goal.category_id:
        return GoalScope((goal.category_id,), (), whole_spend=False)
    return GoalScope((), (), whole_spend=True)


def largest_increases(changes: list[CategoryChange], limit: int) -> list[CategoryChange]:
    """The categories that grew the most, by amount rather than percentage (BRD F2).

    By amount, so a category going from 1 to 10 does not outrank one going from
    500 to 900; a category new this period counts too, though it has no percentage.
    """
    grown = [c for c in changes if c.change > 0]
    grown.sort(key=lambda c: (-c.change, c.standing.name or ""))
    return grown[:limit]


@dataclass(frozen=True)
class RecurringItem:
    """A product bought on several receipts, and where it is bought most (BRD F2).

    `receipt_count` counts receipts, not lines: two lines of it on one receipt are
    one purchase occasion. `merchant_receipts` of the `merchant_receipt_total`
    receipts from `merchant` contain it — "9 of your 14 Fresh Market receipts".
    `merchant` is None when no receipt carrying it names a shop.
    """

    name: str
    receipt_count: int
    total: Decimal
    merchant: str | None
    merchant_receipts: int
    merchant_receipt_total: int


@dataclass(frozen=True)
class GoalAnalysis:
    """Everything advice on one goal may cite, over one window of history (BRD F2).

    `compared_with` is the like-for-like period before `window` that
    `largest_increases` are measured against. `receipt_count` is how many receipts
    the window holds, for the insufficient-data guard (F5, F8.6) to judge.
    `recurring_items` come from all spending when the goal names none in particular
    (`scope.whole_spend`), otherwise only from what it concerns.
    """

    goal: GoalBrief
    scope: GoalScope
    window: DateRange
    compared_with: DateRange
    receipt_count: int
    highest_spend: list[CategoryStanding]
    largest_increases: list[CategoryChange]
    goal_categories: list[CategoryStanding]
    recurring_items: list[RecurringItem]


def render_advice_context(analysis: GoalAnalysis, currency: str) -> str:
    """The analysis as the advice model reads it: the goal, then the evidence (F8.3.2).

    Every section is present even when empty, and says so, so the model is never
    left to fill a gap from general knowledge (BRD F3, constraint 11.3).
    """
    goal = analysis.goal

    def money(amount: Decimal) -> str:
        return f"{amount:.2f} {currency}"

    def standing(c: CategoryStanding) -> str:
        return (
            f"- {c.name or 'Uncategorized'}: {money(c.total)}, "
            f"{c.share}% of spending, {c.item_count} items"
        )

    lines = [f"Goal: {goal.name} ({_kind(goal)})"]
    if goal.description:
        lines.append(f"In the user's words: {goal.description}")
    if goal.target_amount is not None:
        lines.append(f"Target: {_target(goal, money(goal.target_amount))}")
    lines.append(
        f"History analysed: {_day(analysis.window.start)} to {_day(analysis.window.end)}, "
        f"{analysis.receipt_count} receipts."
    )

    lines += ["", "## Highest spending categories"]
    lines += [standing(c) for c in analysis.highest_spend] or ["- none in this period"]

    lines += [
        "",
        f"## Largest increases against {_day(analysis.compared_with.start)} "
        f"to {_day(analysis.compared_with.end)}",
    ]
    lines += [
        f"- {c.standing.name or 'Uncategorized'}: +{money(c.change)} "
        + (f"(+{c.change_percent}%)" if c.change_percent is not None else "(new this period)")
        for c in analysis.largest_increases
    ] or ["- no category grew"]

    if not analysis.scope.whole_spend:
        lines += ["", "## Spending in the categories this goal concerns"]
        lines += [standing(c) for c in analysis.goal_categories] or [
            "- nothing spent in them in this period"
        ]

    lines += [
        "",
        "## Most frequent purchases"
        if analysis.scope.whole_spend
        else "## Recurring purchases related to this goal",
    ]
    lines += [_recurring(item, money) for item in analysis.recurring_items] or [
        "- no purchase recurs in this period"
    ]
    return "\n".join(lines)


_KIND_NAMES = {
    FinancialKind.SPENDING_CEILING: "monthly spending ceiling",
    FinancialKind.SAVINGS_TARGET: "savings target",
    FinancialKind.CATEGORY_REDUCTION: "spend less on one category",
}


def _kind(goal: GoalBrief) -> str:
    if goal.type is GoalType.LIFESTYLE:
        return "lifestyle goal, read through what is bought"
    if goal.financial_kind is None:
        return "money goal"
    return _KIND_NAMES[goal.financial_kind]


def _target(goal: GoalBrief, amount: str) -> str:
    if goal.financial_kind is FinancialKind.SAVINGS_TARGET:
        return f"put {amount} aside"
    if goal.financial_kind is FinancialKind.CATEGORY_REDUCTION:
        return f"keep {goal.category_name or 'the category'} under {amount} a month"
    return f"stay under {amount} a month"


def _recurring(item: RecurringItem, money: Callable[[Decimal], str]) -> str:
    line = f"- {item.name}: on {item.receipt_count} receipts, {money(item.total)} in all"
    if item.merchant:
        line += (
            f"; on {item.merchant_receipts} of the {item.merchant_receipt_total} "
            f"receipts from {item.merchant}"
        )
    return line


def _day(day: date) -> str:
    return f"{day.day} {day:%B %Y}"
