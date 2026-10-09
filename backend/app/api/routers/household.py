"""The caller's household (F12.2, ADR-0017)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import rate_limit
from app.api.dependencies import get_current_user
from app.api.rate_limit import limiter
from app.db.session import get_db_session
from app.models.household import Household, HouseholdRole
from app.models.user import User
from app.repository.household import HouseholdRepository
from app.schemas.household import (
    HouseholdInvite,
    HouseholdMemberRead,
    HouseholdName,
    HouseholdRead,
    JoinRequest,
)
from app.services.household import HouseholdService

router = APIRouter(prefix="/api/v1/household", tags=["household"])


def get_household_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> HouseholdService:
    """The household service bound to the request's session."""
    return HouseholdService(HouseholdRepository(session))


Service = Annotated[HouseholdService, Depends(get_household_service)]
CurrentUser = Annotated[User, Depends(get_current_user)]


def _read(household: Household, user: User) -> HouseholdRead:
    members = [
        HouseholdMemberRead(
            user_id=m.user_id,
            first_name=m.user.first_name,
            last_name=m.user.last_name,
            email=m.user.email,
            role=m.role,
            joined_at=m.created_at,
        )
        for m in household.members
    ]
    my_role = next(m.role for m in household.members if m.user_id == user.id)
    return HouseholdRead(
        id=household.id,
        name=household.name,
        my_role=my_role,
        members=members,
        invite_code=household.invite_code if my_role == HouseholdRole.OWNER else None,
    )


@router.get("", response_model=HouseholdRead | None)
async def get_my_household(current_user: CurrentUser, service: Service) -> HouseholdRead | None:
    """The caller's household with its members, or null when they have none."""
    household = await service.mine(current_user)
    return _read(household, current_user) if household else None


@router.post("", response_model=HouseholdRead, status_code=status.HTTP_201_CREATED)
async def create_household(
    request: HouseholdName, current_user: CurrentUser, service: Service
) -> HouseholdRead:
    """Start a household owned by the caller; 409 if they already belong to one."""
    return _read(await service.create(current_user, request.name), current_user)


@router.patch("", response_model=HouseholdRead)
async def rename_household(
    request: HouseholdName, current_user: CurrentUser, service: Service
) -> HouseholdRead:
    """Rename the caller's household; 403 unless they own it."""
    return _read(await service.rename(current_user, request.name), current_user)


@router.post("/leave", status_code=status.HTTP_204_NO_CONTENT)
async def leave_household(current_user: CurrentUser, service: Service) -> None:
    """Leave the caller's household; 409 for an owner with members left."""
    await service.leave(current_user)


@router.delete("/members/{user_id}", response_model=HouseholdRead)
async def remove_member(
    user_id: uuid.UUID, current_user: CurrentUser, service: Service
) -> HouseholdRead:
    """The owner removes a member, whose access ends at once; 404 for anyone not in it."""
    return _read(await service.remove_member(current_user, user_id), current_user)


@router.post("/invite/regenerate", response_model=HouseholdRead)
async def regenerate_invite(current_user: CurrentUser, service: Service) -> HouseholdRead:
    """A new invite link for the household; the old one stops working (owner only)."""
    return _read(await service.regenerate_invite(current_user), current_user)


@router.get("/invites/{code}", response_model=HouseholdInvite)
@limiter.shared_limit(rate_limit.JOIN, scope="household-invites")
async def read_invite(
    request: Request, code: str, current_user: CurrentUser, service: Service
) -> HouseholdInvite:
    """Whose household an invite link leads to, before joining; 404 for a dead link."""
    household = await service.invited_to(code)
    owner = next(m.user for m in household.members if m.role == HouseholdRole.OWNER)
    return HouseholdInvite(
        name=household.name,
        owner_name=f"{owner.first_name} {owner.last_name}".strip(),
        member_count=len(household.members),
    )


@router.post("/join", response_model=HouseholdRead)
@limiter.shared_limit(rate_limit.JOIN, scope="household-invites")
async def join_household(
    request: Request, body: JoinRequest, current_user: CurrentUser, service: Service
) -> HouseholdRead:
    """Join by invite link (F12.3); 409 when already in one or in another currency."""
    return _read(await service.join(current_user, body.code), current_user)
