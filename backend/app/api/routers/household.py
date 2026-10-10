"""The caller's household (F12.2, ADR-0017)."""

import uuid
from datetime import UTC, date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import rate_limit
from app.api.dependencies import get_current_user
from app.api.periods import required_period
from app.api.rate_limit import limiter
from app.db.session import get_db_session
from app.domain.budget import BudgetMonth
from app.domain.periods import DateRange
from app.models.household import Household, HouseholdRole
from app.models.user import User
from app.repository.household import HouseholdRepository
from app.repository.household_spend import HouseholdSpendRepository
from app.schemas.household import (
    HouseholdBudgetRequest,
    HouseholdCategoryResponse,
    HouseholdInvite,
    HouseholdMemberRead,
    HouseholdMonthResponse,
    HouseholdName,
    HouseholdRead,
    HouseholdStatisticsResponse,
    JoinRequest,
    LimitUsageResponse,
    MemberShareResponse,
)
from app.services.household import HouseholdService
from app.services.household_budget import HouseholdBudgetService

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
        budget_limit=household.budget_limit,
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


def get_household_budget_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> HouseholdBudgetService:
    """The household's month and statistics, bound to the request's session."""
    return HouseholdBudgetService(
        HouseholdService(HouseholdRepository(session)), HouseholdSpendRepository(session)
    )


Budget = Annotated[HouseholdBudgetService, Depends(get_household_budget_service)]


@router.put("/budget", response_model=HouseholdRead)
async def set_household_budget(
    body: HouseholdBudgetRequest, current_user: CurrentUser, service: Service
) -> HouseholdRead:
    """Set or clear the household's monthly budget (F12.5, D7); 403 unless the owner."""
    return _read(await service.set_budget(current_user, body.budget_limit), current_user)


@router.get("/months/{year}/{month}", response_model=HouseholdMonthResponse)
async def get_household_month(
    year: Annotated[int, Path(ge=1970, le=9999)],
    month: Annotated[int, Path(ge=1, le=12)],
    current_user: CurrentUser,
    budget: Budget,
    today: Annotated[date | None, Query()] = None,
) -> HouseholdMonthResponse:
    """The household's spend in one month, against its budget, split by member (F12.5).

    Every member's parsed receipts count, private ones included, but a private one only
    as money in its owner's private sum (ADR-0017). `today` is the user's own date, as
    for the personal month (ADR-0009). 404 outside a household.
    """
    summary = await budget.month(
        current_user, BudgetMonth(year, month), today or datetime.now(UTC).date()
    )
    return HouseholdMonthResponse(
        year=year,
        month=month,
        total=summary.total,
        receipt_count=summary.receipt_count,
        is_complete=summary.progress.is_complete,
        days_elapsed=summary.progress.days_elapsed,
        days=summary.progress.days,
        excluded_count=summary.excluded_count,
        excluded_amount=summary.excluded_amount,
        limit=LimitUsageResponse(
            limit=summary.limit.limit,
            percent=summary.limit.percent,
            remaining=summary.limit.remaining,
        )
        if summary.limit
        else None,
        members=[
            MemberShareResponse(
                user_id=m.user_id,
                first_name=m.first_name,
                shared_total=m.shared_total,
                private_total=m.private_total,
                total=m.total,
            )
            for m in summary.members
        ],
    )


@router.get("/statistics", response_model=HouseholdStatisticsResponse)
async def get_household_statistics(
    period: Annotated[DateRange, Depends(required_period)],
    current_user: CurrentUser,
    budget: Budget,
) -> HouseholdStatisticsResponse:
    """The household's spend by category between two dates, private as one row (F12.5).

    Only shared receipts give categories; private spend is a single figure, so nothing
    in it says what was bought (ADR-0017). 404 outside a household.
    """
    stats = await budget.statistics(current_user, period)
    return HouseholdStatisticsResponse(
        start=period.start.isoformat(),
        end=period.end.isoformat(),
        total=stats.total,
        categories=[
            HouseholdCategoryResponse(
                category_id=c.spend.category_id,
                name=c.spend.name,
                owner_id=c.spend.owner_id,
                item_count=c.spend.item_count,
                total=c.spend.total,
                share=c.share,
            )
            for c in stats.categories
        ],
        private_total=stats.private_total,
        private_share=stats.private_share,
    )
