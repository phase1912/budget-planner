import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.domain.goals import FinancialKind, GoalType

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
Description = Annotated[str, StringConstraints(strip_whitespace=True, max_length=1000)]
Amount = Annotated[Decimal, Field(max_digits=12, decimal_places=2)]


class GoalCreate(BaseModel):
    """A new goal as the user states it (BRD F1).

    Whether its fields fit together — a money goal's kind, amount and category,
    or a lifestyle goal's lack of them — is checked by `app.domain.goals`.
    """

    type: GoalType
    name: Name
    description: Description | None = None
    financial_kind: FinancialKind | None = None
    target_amount: Amount | None = None
    category_id: uuid.UUID | None = None


class GoalUpdate(BaseModel):
    """A change to a goal: only the fields sent change (BRD F1).

    `name` cannot be cleared. `description`, `target_amount` and `category_id` can
    be sent as null to clear them; the result must still be a well formed goal. A
    goal's type is fixed once made.
    """

    name: Name | None = None
    description: Description | None = None
    financial_kind: FinancialKind | None = None
    target_amount: Amount | None = None
    category_id: uuid.UUID | None = None


class GoalRead(BaseModel):
    """A goal as the Goals screen shows it; `mapped_*` are filled by F8.2 (F9)."""

    id: uuid.UUID
    type: GoalType
    name: str
    description: str | None
    financial_kind: FinancialKind | None
    target_amount: Decimal | None
    category_id: uuid.UUID | None
    mapped_category_ids: list[uuid.UUID]
    mapped_item_names: list[str]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
