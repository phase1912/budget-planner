from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, computed_field

from app.core.config import get_settings
from app.domain.email_intake import forwarding_address


class UserResponse(BaseModel):
    """Public representation of a user (F1.1)."""

    id: UUID
    email: EmailStr
    first_name: str
    last_name: str
    currency: str
    budget_limit: Decimal | None = None
    forwarding_token: str = Field(exclude=True)

    model_config = ConfigDict(from_attributes=True)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def forwarding_address(self) -> str:
        """Where the user forwards e-receipts (F11.2); only ever shown to its owner."""
        return forwarding_address(self.forwarding_token, get_settings().inbound_email_domain)


class UserUpdateRequest(BaseModel):
    """Payload for updating user preferences (F1.4)."""

    currency: str | None = Field(None, min_length=3, max_length=3, pattern=r"^[A-Z]{3}$")
    # Spend is shown as a share of it (D7), so zero or less is not a limit; null removes it.
    budget_limit: Decimal | None = Field(None, gt=0, max_digits=12, decimal_places=2)
