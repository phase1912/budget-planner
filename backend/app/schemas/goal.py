import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.domain.goal_check import Unknown, Verdict
from app.domain.goals import (
    WATCHED_ITEM_MAX_LENGTH,
    WATCHED_LINES_MAX,
    FinancialKind,
    GoalType,
)

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
Description = Annotated[str, StringConstraints(strip_whitespace=True, max_length=1000)]
Amount = Annotated[Decimal, Field(max_digits=12, decimal_places=2)]
ItemName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=WATCHED_ITEM_MAX_LENGTH)
]
WatchedCategories = Annotated[list[uuid.UUID], Field(max_length=WATCHED_LINES_MAX)]
WatchedItems = Annotated[list[ItemName], Field(max_length=WATCHED_LINES_MAX)]


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
    target_date: date | None = None
    saved_account_id: uuid.UUID | None = None
    saved_amount: Amount | None = None


class GoalUpdate(BaseModel):
    """A change to a goal: only the fields sent change (BRD F1).

    `name` cannot be cleared. `description`, `target_amount` and `category_id` can
    be sent as null to clear them; the result must still be a well formed goal. A
    goal's type is fixed once made. Sending `mapped_*` is the user correcting what
    a lifestyle goal watches (F8.2); an empty list clears it, null is refused. A savings
    goal's `target_date`, `saved_account_id` and `saved_amount` can be set or cleared
    (F8.11.1).
    """

    name: Name | None = None
    description: Description | None = None
    financial_kind: FinancialKind | None = None
    target_amount: Amount | None = None
    category_id: uuid.UUID | None = None
    target_date: date | None = None
    saved_account_id: uuid.UUID | None = None
    saved_amount: Amount | None = None
    mapped_category_ids: WatchedCategories | None = None
    mapped_item_names: WatchedItems | None = None


class GoalRead(BaseModel):
    """A goal as the Goals screen shows it; `mapped_*` are filled by F8.2 (F9); a savings
    goal's date and where its money is come with it (F8.11.1)."""

    id: uuid.UUID
    type: GoalType
    name: str
    description: str | None
    financial_kind: FinancialKind | None
    target_amount: Decimal | None
    category_id: uuid.UUID | None
    mapped_category_ids: list[uuid.UUID]
    mapped_item_names: list[str]
    target_date: date | None = None
    saved_account_id: uuid.UUID | None = None
    saved_amount: Decimal | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GoalCheckRequest(BaseModel):
    """A money goal to check before it is saved (F23.13); `today` is the caller's date."""

    financial_kind: FinancialKind
    target_amount: Annotated[Amount, Field(gt=0)]
    category_id: uuid.UUID | None = None
    today: date | None = None
    target_date: date | None = None
    """A savings goal's date: it is checked as what must be put aside a month to reach it."""


class GoalCheckSource(BaseModel):
    """A category the gap could come from: its monthly spend and the suggested cut."""

    category_id: uuid.UUID | None
    name: str | None
    monthly: Decimal
    cut: Decimal


class GoalCheckSwap(BaseModel):
    """A product to buy at `shop` instead of `instead_of`, and what that saves a month."""

    name: str
    shop: str
    instead_of: str
    monthly_saving: Decimal


class GoalCheckResponse(BaseModel):
    """The verdict: `doable`, a `stretch` with sources, or `unknown` with the reason.

    `usual` is what the goal is measured against (monthly spend, the category's monthly
    spend, or what is usually left for a savings target), over `months` recent months.
    """

    verdict: Verdict
    usual: Decimal | None
    gap: Decimal
    months: int
    sources: list[GoalCheckSource]
    unknown: Unknown | None
    swaps: list[GoalCheckSwap] = []
    """Products to buy where the family has seen them cheaper (F12.11)."""
    family: bool = False
