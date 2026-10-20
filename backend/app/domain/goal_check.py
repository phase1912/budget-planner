"""Whether a money goal is within reach before it is saved (F23.13).

A calm, numbers-only check: it compares the goal with what the user's own receipts and
income show for recent months, and when the goal is a stretch it names where the money
could come from — the categories most is spent on, each trimmed by a modest share.
"""

import enum
import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

from app.domain.family_lines import Swap
from app.domain.goals import FinancialKind

TRIM = Decimal("0.15")
"""The share of a category's monthly spend suggested as a cut: noticeable, not drastic."""

MAX_SOURCES = 3
WHOLE = Decimal("1")


class Verdict(enum.StrEnum):
    """What the check concludes: in reach, a stretch, or not enough to tell."""

    DOABLE = "doable"
    STRETCH = "stretch"
    UNKNOWN = "unknown"


class Unknown(enum.StrEnum):
    """Why a goal could not be checked."""

    NO_HISTORY = "no_history"
    NO_INCOME = "no_income"


@dataclass(frozen=True)
class MonthlyCategory:
    """A category's average monthly spend over the months checked."""

    category_id: uuid.UUID | None
    name: str | None
    monthly: Decimal


@dataclass(frozen=True)
class Source:
    """A category the gap could come from, and how much a month."""

    category_id: uuid.UUID | None
    name: str | None
    monthly: Decimal
    cut: Decimal


@dataclass(frozen=True)
class GoalCheck:
    """The verdict with the figures behind it.

    `usual` is what the goal is measured against: the monthly spend for a ceiling, the
    category's monthly spend for a cut, or what is usually left at a month's end for a
    savings target. `gap` is how far the goal is beyond it (zero when doable).
    """

    verdict: Verdict
    usual: Decimal | None
    gap: Decimal
    months: int
    sources: list[Source]
    unknown: Unknown | None = None
    swaps: list[Swap] = field(default_factory=list)
    """Products to buy where the family has seen them cheaper, and what each saves (F12.11)."""
    family: bool = False
    """Whether `swaps` come from the whole family's shared receipts, not the user's alone."""


def check_goal_plan(
    kind: FinancialKind,
    target: Decimal,
    *,
    category_id: uuid.UUID | None,
    months: int,
    monthly_spend: Decimal,
    categories: Sequence[MonthlyCategory],
    monthly_income: Decimal | None,
) -> GoalCheck:
    """Check a monthly money goal against recent months.

    `months` is how many recent months had receipts; with none there is nothing to
    compare and the verdict is unknown. A savings target is a sum put aside each month,
    so it needs an income; without one it cannot be checked either. A goal already
    within what the months show is doable; beyond it, a stretch, with sources for a
    ceiling or a savings target (a cut to one category is its own source).
    """
    if months == 0:
        return GoalCheck(Verdict.UNKNOWN, None, Decimal(0), 0, [], Unknown.NO_HISTORY)
    if kind is FinancialKind.SAVINGS_TARGET:
        if monthly_income is None:
            return GoalCheck(Verdict.UNKNOWN, None, Decimal(0), months, [], Unknown.NO_INCOME)
        usual = monthly_income - monthly_spend
        gap = target - usual
    elif kind is FinancialKind.CATEGORY_REDUCTION:
        usual = next((c.monthly for c in categories if c.category_id == category_id), Decimal(0))
        gap = usual - target
    else:
        usual = monthly_spend
        gap = usual - target

    usual = usual.quantize(WHOLE, ROUND_HALF_UP)
    gap = max(gap, Decimal(0)).quantize(WHOLE, ROUND_HALF_UP)
    if gap == 0:
        return GoalCheck(Verdict.DOABLE, usual, gap, months, [])
    sources = [] if kind is FinancialKind.CATEGORY_REDUCTION else _sources(categories, gap)
    return GoalCheck(Verdict.STRETCH, usual, gap, months, sources)


def _sources(categories: Sequence[MonthlyCategory], gap: Decimal) -> list[Source]:
    sources: list[Source] = []
    left = gap
    for category in sorted(categories, key=lambda c: c.monthly, reverse=True):
        if left <= 0 or len(sources) == MAX_SOURCES:
            break
        cut = min((category.monthly * TRIM).quantize(WHOLE, ROUND_HALF_UP), left)
        if cut <= 0:
            continue
        sources.append(Source(category.category_id, category.name, category.monthly, cut))
        left -= cut
    return sources
