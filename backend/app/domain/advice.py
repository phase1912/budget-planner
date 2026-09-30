"""What counts as advice on a goal, and what is refused as generic (BRD F3, 11.3 — F8.4).

A recommendation must name a category or a recurring purchase the analysis found
in the user's own receipts. One that names anything else is a generic tip by
definition, however it is worded, and is never kept.
"""

import enum
from dataclasses import dataclass

from app.domain.goal_analysis import GoalAnalysis

ADVICE_MAX = 3
"""How many recommendations one request for advice keeps."""

TARGET_MAX_LENGTH = 255
ACTION_MAX_LENGTH = 255


class AdviceTarget(enum.StrEnum):
    """What a recommendation is about: a whole category, or one recurring purchase."""

    CATEGORY = "category"
    ITEM = "item"


@dataclass(frozen=True)
class Advice:
    """One recommendation as proposed: its target by name, the action, and why."""

    target_kind: AdviceTarget
    target_name: str
    action: str
    rationale: str


def cited_names(analysis: GoalAnalysis) -> dict[AdviceTarget, set[str]]:
    """Every category and purchase the analysis names, case-folded, by kind."""
    categories = {
        c.name
        for c in [*analysis.highest_spend, *analysis.goal_categories]
        + [change.standing for change in analysis.largest_increases]
        if c.name
    }
    return {
        AdviceTarget.CATEGORY: {name.casefold() for name in categories},
        AdviceTarget.ITEM: {item.name.casefold() for item in analysis.recurring_items},
    }


def keep_specific(proposed: list[Advice], analysis: GoalAnalysis) -> list[Advice]:
    """The proposals that name something the analysis found, one per target (BRD F3).

    A target outside the evidence is generic advice or an invention; both are
    dropped (constraint 11.3). Proposals with an empty action are dropped too.
    Order is kept, at most ADVICE_MAX; text is trimmed to what the columns hold.
    """
    names = cited_names(analysis)
    kept: list[Advice] = []
    seen: set[tuple[AdviceTarget, str]] = set()
    for advice in proposed:
        target = advice.target_name.strip()
        key = (advice.target_kind, target.casefold())
        if key[1] not in names[advice.target_kind] or key in seen or not advice.action.strip():
            continue
        seen.add(key)
        kept.append(
            Advice(
                target_kind=advice.target_kind,
                target_name=target[:TARGET_MAX_LENGTH],
                action=advice.action.strip()[:ACTION_MAX_LENGTH],
                rationale=advice.rationale.strip(),
            )
        )
    return kept[:ADVICE_MAX]
