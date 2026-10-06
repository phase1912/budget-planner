"""What counts as advice on a goal, and what following it is worth (BRD F3, F4, 11.3).

A recommendation must name a category or a recurring purchase the analysis found
in the user's own receipts. One that names anything else is a generic tip by
definition, however it is worded, and is never kept (F8.4). What following it is
worth is computed here from that same history, never taken from the model (F8.5).
"""

import enum
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from app.domain.goal_analysis import DismissedRecommendation, GoalAnalysis

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
    """One recommendation as proposed: its target by name, the action, and why.

    `reduction_percent` is the share of the spending on the target the action
    removes: 100 to stop buying it, 50 to halve it. It is the only number taken
    from the model, and only as a reading of its own action.
    """

    target_kind: AdviceTarget
    target_name: str
    action: str
    rationale: str
    reduction_percent: int


def _evidence(analysis: GoalAnalysis) -> dict[tuple[AdviceTarget, str], tuple[Decimal, int | None]]:
    """What the analysis says was spent on each target it names, over its window.

    Keyed by kind and case-folded name; each value is the spend and, for a
    recurring purchase, how many receipts carried it.
    """
    evidence: dict[tuple[AdviceTarget, str], tuple[Decimal, int | None]] = {}
    standings = [
        *analysis.highest_spend,
        *analysis.goal_categories,
        *(change.standing for change in analysis.largest_increases),
    ]
    for c in standings:
        if c.name:
            evidence[(AdviceTarget.CATEGORY, c.name.casefold())] = (c.total, None)
    for item in analysis.recurring_items:
        evidence[(AdviceTarget.ITEM, item.name.casefold())] = (item.total, item.receipt_count)
    return evidence


def keep_specific(proposed: list[Advice], analysis: GoalAnalysis) -> list[Advice]:
    """The proposals that name something the analysis found, one per target (BRD F3).

    A target outside the evidence is generic advice or an invention; both are
    dropped (constraint 11.3). So are proposals with an empty action, or one
    removing nothing; a reduction is capped at 100%. Order is kept, at most
    ADVICE_MAX; text is trimmed to what the columns hold.
    """
    names = _evidence(analysis)
    kept: list[Advice] = []
    seen: set[tuple[AdviceTarget, str]] = set()
    for advice in proposed:
        target = advice.target_name.strip()
        key = (advice.target_kind, target.casefold())
        if (
            key not in names
            or key in seen
            or not advice.action.strip()
            or advice.reduction_percent < 1
        ):
            continue
        seen.add(key)
        kept.append(
            Advice(
                target_kind=advice.target_kind,
                target_name=target[:TARGET_MAX_LENGTH],
                action=advice.action.strip()[:ACTION_MAX_LENGTH],
                rationale=advice.rationale.strip(),
                reduction_percent=min(advice.reduction_percent, 100),
            )
        )
    return kept[:ADVICE_MAX]


AVERAGE_MONTH_DAYS = Decimal("30.4375")
"""A calendar month on average (365.25 / 12), to turn a window of days into months."""


@dataclass(frozen=True)
class ProjectedImpact:
    """What following one recommendation is worth each month (BRD F4).

    `monthly_saving` is the money; `purchases_avoided` is how many fewer times a
    month a recurring purchase is bought, and None for a whole category. Both
    are the target's average monthly spend over the analysis window, times the
    advice's `reduction_percent`.
    """

    monthly_saving: Decimal
    purchases_avoided: Decimal | None


def project_impact(advice: Advice, analysis: GoalAnalysis) -> ProjectedImpact:
    """Work out what `advice` saves from the history in `analysis` alone (BRD F4 — F8.5).

    `advice` must be one `keep_specific` kept from this analysis, so its target
    is in the evidence; raises KeyError otherwise. A target whose net spend is
    negative (refunds) saves nothing rather than costing money.
    """
    spend, receipts = _evidence(analysis)[(advice.target_kind, advice.target_name.casefold())]
    months = Decimal(analysis.window.days) / AVERAGE_MONTH_DAYS
    share = Decimal(advice.reduction_percent) / 100
    saving = max(spend, Decimal(0)) / months * share
    avoided = Decimal(receipts) / months * share if receipts is not None else None
    return ProjectedImpact(
        monthly_saving=saving.quantize(Decimal("0.01"), ROUND_HALF_UP),
        purchases_avoided=avoided.quantize(Decimal("0.1"), ROUND_HALF_UP)
        if avoided is not None
        else None,
    )


@dataclass(frozen=True)
class AdviceReadiness:
    """Whether there is enough history behind advice yet, and how close it is (BRD F5).

    Advice needs both `required_receipts` parsed receipts and `required_days` of
    history since the first of them: a pile of receipts uploaded in one afternoon is
    not a pattern, and neither is a month with two receipts in it.
    """

    receipts: int
    required_receipts: int
    history_days: int
    required_days: int

    @property
    def ready(self) -> bool:
        """Both minimums are met."""
        return self.receipts >= self.required_receipts and self.history_days >= self.required_days

    @property
    def progress(self) -> int:
        """How far along the slower of the two minimums is, as a whole percentage, 0-100."""
        receipts = self.receipts / self.required_receipts
        days = self.history_days / self.required_days
        return int(min(receipts, days, 1.0) * 100)


def assess_readiness(
    receipts: int,
    first_purchase: date | None,
    as_of: date,
    *,
    required_receipts: int,
    required_days: int,
) -> AdviceReadiness:
    """How much history the user has for advice, against the configured minimums (F5).

    `receipts` counts parsed receipts only, the ones that also count toward the
    month; `first_purchase` is the earliest of them. History is the days from it
    to `as_of`; with no receipt at all there is none.
    """
    days = max((as_of - first_purchase).days, 0) if first_purchase else 0
    return AdviceReadiness(receipts, required_receipts, days, required_days)


def demote_dismissed(
    advice: list[Advice], dismissed: list[DismissedRecommendation]
) -> list[Advice]:
    """Rank fresh advice on a target the user already turned down last (F8.9).

    The model is told not to repeat turned-down advice, but that is a request, not
    a guarantee; this makes it hold regardless. Nothing is dropped: cutting the same
    category another way may still be the right call. Order is otherwise kept.
    """
    turned_down = {d.target_name.casefold() for d in dismissed}
    return sorted(advice, key=lambda a: a.target_name.casefold() in turned_down)
