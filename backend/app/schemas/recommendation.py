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
