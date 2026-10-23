"""The admin console at the API boundary (F18.6): account facts, never receipts (N2)."""

import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field

from app.domain.admin import MAX_GRANT_DAYS


class AdminUserRow(BaseModel):
    """One account in the admin list."""

    id: uuid.UUID
    email: str
    first_name: str
    last_name: str
    created_at: datetime
    email_confirmed: bool
    is_admin: bool
    plan: str
    last_active_at: datetime | None


class AdminUsersPage(BaseModel):
    items: list[AdminUserRow]
    total: int


class PlanGrantRead(BaseModel):
    id: uuid.UUID
    plan: str
    starts_at: datetime
    ends_at: datetime
    reason: str
    granted_by: str | None
    revoked_at: datetime | None
    created_at: datetime


class ActivityRead(BaseModel):
    event: str
    created_at: datetime


class AdminUserCard(BaseModel):
    """What an admin sees about one account: who, how it is set up, how it is used."""

    id: uuid.UUID
    email: str
    first_name: str
    last_name: str
    created_at: datetime
    email_confirmed_at: datetime | None
    onboarded_at: datetime | None
    language: str | None
    terms_version: str | None
    is_admin: bool
    is_super_admin: bool
    two_factor_enabled: bool
    plan: str
    plan_ends_on: date | None
    credits_limit: int | None
    credits_used: int
    last_active_at: datetime | None
    grants: list[PlanGrantRead]
    activity: list[ActivityRead]


class PlanGrantRequest(BaseModel):
    """Give the paid plan for `days` more days, saying why (F18.6.3)."""

    days: int = Field(ge=1, le=MAX_GRANT_DAYS)
    reason: str = Field(min_length=3, max_length=200)


class AdminRoleRequest(BaseModel):
    admin: bool


class AdminActionRead(BaseModel):
    """One entry of the admin log."""

    id: uuid.UUID
    created_at: datetime
    action: str
    admin: str | None
    target: str | None
    details: dict[str, Any]


class AdminLogPage(BaseModel):
    items: list[AdminActionRead]


class ReplyReportRead(BaseModel):
    """An assistant reply a user reported (F22.4.2): its words, why, by whom and when."""

    id: uuid.UUID
    created_at: datetime
    reason: str
    reply_text: str
    reporter: str | None
