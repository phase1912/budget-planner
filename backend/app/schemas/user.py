from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr


class UserResponse(BaseModel):
    """Public representation of a user (F1.1)."""

    id: UUID
    email: EmailStr
    first_name: str
    last_name: str
    currency: str
    budget_limit: Decimal | None = None

    model_config = ConfigDict(from_attributes=True)
