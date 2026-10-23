"""Household API models (F12.2)."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

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
    owner_sets_budget: bool = False
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


class MemberRoleRequest(BaseModel):
    """What the owner makes a member: an adult, or a child who changes nothing (F12.10)."""

    role: Literal["adult", "child"]


class BudgetKeeperRequest(BaseModel):
    """Whether only the owner changes the household budget (F12.10)."""

    owner_only: bool


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


class MemberTotalResponse(BaseModel):
    """What one member spent of something (F12.9)."""

    user_id: uuid.UUID
    total: Decimal


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
    # What the household shares this month (F12.8): income in and bills out.
    shared_income: Decimal = Decimal(0)
    shared_bills: Decimal = Decimal(0)


class HouseholdCategoryResponse(BaseModel):
    """A category's part of the household's shared spend; `owner_id` for a member's own."""

    category_id: uuid.UUID | None
    name: str | None
    owner_id: uuid.UUID | None
    item_count: int
    total: Decimal
    share: Decimal
    # Who bought it, by member (F12.9); shared receipts only.
    members: list[MemberTotalResponse] = []


class HouseholdStatisticsResponse(BaseModel):
    """The household's spend by category for a period, private spend as one figure."""

    start: str
    end: str
    total: Decimal
    categories: list[HouseholdCategoryResponse]
    private_total: Decimal
    private_share: Decimal


class HouseholdMemberDayResponse(BaseModel):
    """What one member spent on a day."""

    user_id: uuid.UUID
    total: Decimal


class HouseholdDayResponse(BaseModel):
    """One day with each member's spending on it, in the order of `members`."""

    day: date
    members: list[HouseholdMemberDayResponse]


class HouseholdDailyMemberResponse(BaseModel):
    """A member as the daily chart names them."""

    user_id: uuid.UUID
    first_name: str


class TwiceResponse(BaseModel):
    """A product two members bought within three days (F12.11)."""

    name: str
    members: list[uuid.UUID]
    days: list[date]
    paid: Decimal


class ProductMembersResponse(BaseModel):
    """What the family paid for one product, and by whom (F12.11)."""

    name: str
    total: Decimal
    members: list[MemberTotalResponse]


class HouseholdLinesResponse(BaseModel):
    """What the family buys, line by line: products bought twice, and who buys what."""

    twice: list[TwiceResponse]
    products: list[ProductMembersResponse]


class HouseholdReceiptResponse(BaseModel):
    """A receipt on the family's chart, with whose it is (F23.22.3, ADR-0017)."""

    id: uuid.UUID
    user_id: uuid.UUID
    merchant_name: str | None
    total: Decimal
    purchased_at: datetime


class HouseholdDailyResponse(BaseModel):
    """The household's spending day by day, per member (F12.5, F23.4).

    `undated_private` is the other members' private spending of the period, which counts in
    the household's totals but is never placed on a day (ADR-0017).
    """

    members: list[HouseholdDailyMemberResponse]
    days: list[HouseholdDayResponse]
    undated_private: Decimal
