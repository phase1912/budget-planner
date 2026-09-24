import uuid
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints


class CategoryOut(BaseModel):
    """A category with its aggregated statistics for the current user."""

    id: uuid.UUID
    name: str
    is_builtin: bool
    item_count: int
    total_amount: Decimal

    model_config = ConfigDict(from_attributes=True)


CategoryName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)
]
"""A category name as the user typed it, trimmed; 100 is the column's width."""


class CategoryCreate(BaseModel):
    """A new custom category (BRD C6)."""

    name: CategoryName


class CategoryUpdate(BaseModel):
    """A new name for one of the user's own categories (BRD C6)."""

    name: CategoryName
