import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.domain.advice import AdviceTarget


class RecommendationRead(BaseModel):
    """One recommendation as its goal's card shows it, with the goal it serves (BRD F3)."""

    id: uuid.UUID
    goal_id: uuid.UUID
    target_kind: AdviceTarget
    target_name: str
    action: str
    rationale: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
