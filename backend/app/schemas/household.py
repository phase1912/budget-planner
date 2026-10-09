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

    model_config = ConfigDict(from_attributes=True)
