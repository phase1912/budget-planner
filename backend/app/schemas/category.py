import uuid
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class CategoryOut(BaseModel):
    """A category with its aggregated statistics for the current user."""

    id: uuid.UUID
    name: str
    is_builtin: bool
    item_count: int
    total_amount: Decimal

    model_config = ConfigDict(from_attributes=True)
