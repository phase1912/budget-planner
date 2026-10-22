import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.domain.advice import AdviceTarget
from app.domain.goal_analysis import FeedbackState
from app.services.goal_progress import GoalStanding


class RecommendationRead(BaseModel):
    """One recommendation as its goal's card shows it, with the goal it serves (BRD F3).

    `monthly_saving` (in the user's currency) and `purchases_avoided` (per month,
    for a recurring purchase only) are computed from the receipts (F4).
    """

    id: uuid.UUID
    goal_id: uuid.UUID
    target_kind: AdviceTarget
    target_name: str
    action: str
    rationale: str
    reduction_percent: int
    monthly_saving: Decimal
    purchases_avoided: Decimal | None
    feedback: FeedbackState | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdviceReadinessRead(BaseModel):
    """Whether advice can be asked for yet, and how far the history has to go (BRD F5).

    `progress` is a whole percentage of the slower of the two minimums, for a meter;
    `analysis_months` how far back advice reads, so an ask that finds nothing can say so
    (F8.11.3).
    """

    ready: bool
    receipts: int
    required_receipts: int
    history_days: int
    required_days: int
    progress: int
    analysis_months: int


class GoalProgressRead(BaseModel):
    """Where a goal stands, worked out live (BRD F6, F7 — F8.11.2); `kind` says which part
    is filled.

    `month` — a ceiling or a category cut: `spent` so far this month, `projected` to the
    month's end at the same daily rate, against the monthly `target`; `margin` how far
    under it the month is heading, negative when over; `day` of `days_in_month` what the
    projection rests on; `at_risk` heading over the cap past the first week (F7);
    `warning_dismissed` the user set this month's warning aside.

    `savings` — `saved` of `target`, `percent` of it, by `target_date`;
    `needed_per_month` to get there in time; `reached`, or `overdue` past its date.

    `lifestyle` — `this_month` on the watched lines against `monthly_average` over the
    three months before, `change_percent` the difference.
    """

    goal_id: uuid.UUID
    goal_name: str
    kind: Literal["month", "savings", "lifestyle"]
    target: Decimal | None = None
    spent: Decimal | None = None
    projected: Decimal | None = None
    margin: Decimal | None = None
    on_track: bool | None = None
    at_risk: bool = False
    warning_dismissed: bool = False
    day: int | None = None
    days_in_month: int | None = None
    saved: Decimal | None = None
    percent: int | None = None
    target_date: date | None = None
    needed_per_month: Decimal | None = None
    reached: bool | None = None
    overdue: bool | None = None
    this_month: Decimal | None = None
    monthly_average: Decimal | None = None
    change_percent: int | None = None

    @classmethod
    def of(cls, standing: GoalStanding, today: date) -> "GoalProgressRead":
        """A goal's standing as the client reads it."""
        goal = standing.goal
        fields: dict[str, object] = {}
        if standing.pace is not None:
            p = standing.pace
            fields = {
                "target": p.target,
                "spent": p.spent,
                "projected": p.projected,
                "margin": p.margin,
                "on_track": p.on_track,
                "at_risk": p.at_risk,
                "warning_dismissed": goal.warning_dismissed_for == today.replace(day=1),
                "day": p.day,
                "days_in_month": p.days_in_month,
            }
        elif standing.savings is not None:
            sv = standing.savings
            fields = {
                "target": sv.target,
                "saved": sv.saved,
                "percent": sv.percent,
                "target_date": sv.target_date,
                "needed_per_month": sv.needed_per_month,
                "reached": sv.reached,
                "overdue": sv.overdue,
            }
        elif standing.lifestyle is not None:
            life = standing.lifestyle
            fields = {
                "this_month": life.this_month,
                "monthly_average": life.monthly_average,
                "change_percent": life.change_percent,
            }
        return cls.model_validate(
            {"goal_id": goal.id, "goal_name": goal.name, "kind": standing.kind, **fields}
        )


class RecommendationFeedbackUpdate(BaseModel):
    """The user's mark on one recommendation; null undoes it (F8.9)."""

    feedback: FeedbackState | None
