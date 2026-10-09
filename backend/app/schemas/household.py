"""Household API models (F12.2)."""

import uuid
from datetime import datetime

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
