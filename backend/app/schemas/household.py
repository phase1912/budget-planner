"""Household API models (F12.2)."""

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class HouseholdName(BaseModel):
    """A household's name, as typed: trimmed, 1 to 60 characters."""

    name: str = Field(min_length=1, max_length=60)

    @field_validator("name", mode="before")
    @classmethod
    def _trimmed(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class HouseholdMemberRead(BaseModel):
    """One person in the household, as the other members see them."""

    user_id: uuid.UUID
    first_name: str
    last_name: str
    email: str
    role: str
    joined_at: datetime


class HouseholdRead(BaseModel):
    """The caller's household, their role in it and who else is in it."""

    id: uuid.UUID
    name: str
    my_role: str
    members: list[HouseholdMemberRead]
    budget_limit: Decimal | None = None
    invite_code: str | None = Field(
        default=None, description="The secret of the invite link; shown to the owner only."
    )

    model_config = ConfigDict(from_attributes=True)


class HouseholdInvite(BaseModel):
    """What an invite link shows before joining: whose household it is, and how big."""

    name: str
    owner_name: str
    member_count: int


class JoinRequest(BaseModel):
    """The code from an invite link."""

    code: str = Field(min_length=1, max_length=64)


class HouseholdBudgetRequest(BaseModel):
    """The household's monthly budget; null removes it (F12.5)."""

    budget_limit: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)


class MemberShareResponse(BaseModel):
    """One member's part of the month: shared spend, and private spend as one sum."""

    user_id: uuid.UUID
    first_name: str
    shared_total: Decimal
    private_total: Decimal
    total: Decimal


class LimitUsageResponse(BaseModel):
    """The month's spend against the household budget (D7)."""

    limit: Decimal
    percent: int
    remaining: Decimal


class HouseholdMonthResponse(BaseModel):
    """The household's month: its total, how far through it is, and who spent what."""

    year: int
    month: int
    total: Decimal
    receipt_count: int
    is_complete: bool
    days_elapsed: int
    days: int
    excluded_count: int
    excluded_amount: Decimal
    limit: LimitUsageResponse | None
    members: list[MemberShareResponse]


class HouseholdCategoryResponse(BaseModel):
    """A category's part of the household's shared spend; `owner_id` for a member's own."""

    category_id: uuid.UUID | None
    name: str | None
    owner_id: uuid.UUID | None
    item_count: int
    total: Decimal
    share: Decimal


class HouseholdStatisticsResponse(BaseModel):
    """The household's spend by category for a period, private spend as one figure."""

    start: str
    end: str
    total: Decimal
    categories: list[HouseholdCategoryResponse]
    private_total: Decimal
    private_share: Decimal
