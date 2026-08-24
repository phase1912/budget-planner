from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserResponse(BaseModel):
    """Public representation of a user (F1.1)."""

    id: UUID
    email: EmailStr
    first_name: str
    last_name: str
    currency: str
    budget_limit: Decimal | None = None

    model_config = ConfigDict(from_attributes=True)


class UserUpdateRequest(BaseModel):
    """Payload for updating user preferences (F1.4)."""

    currency: str | None = Field(None, min_length=3, max_length=3, pattern=r"^[A-Z]{3}$")
    budget_limit: Decimal | None = None
