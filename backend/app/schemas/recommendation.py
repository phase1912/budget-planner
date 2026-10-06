import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.domain.advice import AdviceTarget


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
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdviceReadinessRead(BaseModel):
    """Whether advice can be asked for yet, and how far the history has to go (BRD F5).

    `progress` is a whole percentage of the slower of the two minimums, for a meter.
    """

    ready: bool
    receipts: int
    required_receipts: int
    history_days: int
    required_days: int
    progress: int


class GoalProgressRead(BaseModel):
    """Where a monthly money goal's month is heading, worked out live (BRD F6).

    `spent` so far this month, `projected` to the month's end at the same daily
    rate, against the monthly `target`; `margin` is how far under it the month is
    heading, negative when over. `day` of `days_in_month` is what the projection rests on.
    `at_risk` means heading over the cap past the first week (F7); `warning_dismissed`
    means the user set this month's warning aside.
    """

    goal_id: uuid.UUID
    goal_name: str
    spent: Decimal
    projected: Decimal
    target: Decimal
    margin: Decimal
    on_track: bool
    at_risk: bool
    warning_dismissed: bool
    day: int
    days_in_month: int
