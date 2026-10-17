from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, computed_field

from app.core.config import get_settings
from app.domain.email_intake import forwarding_address

Language = Literal["en", "uk", "pl"]
"""The languages the product is written in (F9.9)."""

Palette = Literal["midnight", "daylight", "rose", "lavender", "sage", "ocean"]
"""The looks a user picks from (F23.1); none chosen means the default, midnight."""


class UserResponse(BaseModel):
    """Public representation of a user (F1.1)."""

    id: UUID
    email: EmailStr
    first_name: str
    last_name: str
    currency: str
    budget_limit: Decimal | None = None
    language: Language | None = None
    email_confirmed: bool = False
    two_factor_enabled: bool = False
    palette: Palette | None = None
    dark_at_night: bool = False
    onboarded_at: datetime | None = None
    travels_for_work: bool = False
    usual_income: Decimal | None = None
    payday: int | None = None
    starting_balance: Decimal | None = None
    balance_since: date | None = None
    forwarding_token: str = Field(exclude=True)
    role: str = Field(default="user", exclude=True)

    model_config = ConfigDict(from_attributes=True)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_admin(self) -> bool:
        """Whether the account sees the admin pages (F17.3.3): by role, or a listed email."""
        admins = {email.lower() for email in get_settings().admin_emails}
        return self.role == "admin" or self.email.lower() in admins

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_super_admin(self) -> bool:
        """Whether the account appoints admins (F18.6.1): an email the deployment lists."""
        return self.email.lower() in {e.lower() for e in get_settings().admin_emails}

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
    language: Language | None = None
    palette: Palette | None = None
    dark_at_night: bool | None = None
    travels_for_work: bool | None = None
    usual_income: Decimal | None = Field(None, ge=0, max_digits=12, decimal_places=2)
    # 31 means the last day of the month, whatever its length.
    payday: int | None = Field(None, ge=1, le=31)
    onboarded: bool | None = None
    """True when the first-sign-in setup is finished or skipped (F23.9)."""
    # Money on the accounts now (F23.14); it may be negative, an overdraft. The date it
    # was true on defaults to the day it is entered.
    starting_balance: Decimal | None = Field(None, max_digits=12, decimal_places=2)
    balance_since: date | None = None


class EmailChangeRequest(BaseModel):
    """Payload for moving the account to another address (F17.8.3); needs the password."""

    email: EmailStr
    password: str


class AccountDeletionRequest(BaseModel):
    """Payload for deleting the account (F17.9.1); the password proves it is the owner."""

    password: str


class TwoFactorSetupRead(BaseModel):
    """What the screen shows to set an authenticator up (F18.6.1)."""

    secret: str
    uri: str
    qr_svg: str


class TwoFactorCodeRequest(BaseModel):
    """A code from the authenticator app."""

    code: str = Field(min_length=6, max_length=16)


class TwoFactorEnabledRead(BaseModel):
    """Two-factor sign-in is on: the recovery codes, shown once, and a session that has it."""

    recovery_codes: list[str]
    access_token: str
    refresh_token: str


class TwoFactorOffRequest(BaseModel):
    """Turning it off takes the password and a code, both."""

    password: str
    code: str = Field(min_length=6, max_length=16)


class ReceiptQuotaRead(BaseModel):
    """The account's receipt reads this month against its limit (F10.6).

    `limit` and `remaining` are null for an account without a limit (an admin). `plan`
    says where the limit comes from and `plan_ends_on` when a granted plan ends (F18.4).
    """

    limit: int | None
    used: int
    remaining: int | None
    unlimited: bool
    resets_on: date
    plan: str
    plan_ends_on: date | None
    ad_free: bool

    model_config = ConfigDict(from_attributes=True)
