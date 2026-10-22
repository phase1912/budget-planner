import uuid
from collections.abc import Sequence
from dataclasses import asdict
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.goal_mapping_agent import GoalMappingAdapter
from app.agent.factory import agent_from_settings
from app.api.dependencies import get_current_user, get_quota_service
from app.db.session import get_db_session
from app.domain.goals import GoalType
from app.models.goal import Goal
from app.models.user import User
from app.ports.goal_mapping import GoalMapperPort
from app.repository.category import CategoryRepository
from app.repository.goal import GoalRepository
from app.schemas.goal import (
    GoalCheckRequest,
    GoalCheckResponse,
    GoalCreate,
    GoalRead,
    GoalUpdate,
)
from app.services.goal import GoalService
from app.services.goal_check import GoalCheckService
from app.services.quota import QuotaService

router = APIRouter(prefix="/api/v1/goals", tags=["goals"])


def get_goal_mapper() -> GoalMapperPort:
    """Provide the goal mapper port; tests override this to stay off the network."""
    return GoalMappingAdapter(agent_from_settings())


def get_goal_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    mapper: Annotated[GoalMapperPort, Depends(get_goal_mapper)],
) -> GoalService:
    """The goal service bound to the request's session."""
    return GoalService(GoalRepository(session), CategoryRepository(session), mapper)


Service = Annotated[GoalService, Depends(get_goal_service)]
CurrentUser = Annotated[User, Depends(get_current_user)]
Quota = Annotated[QuotaService, Depends(get_quota_service)]


@router.get("", response_model=list[GoalRead])
async def list_goals(current_user: CurrentUser, service: Service) -> Sequence[Goal]:
    """The caller's goals, newest first (BRD F1)."""
    return await service.list()


@router.post("", response_model=GoalRead, status_code=status.HTTP_201_CREATED)
async def create_goal(
    request: GoalCreate, current_user: CurrentUser, service: Service, quota: Quota
) -> Goal:
    """State a goal (BRD F1); a malformed one is refused with 422 and the reason.

    A lifestyle goal is mapped by a model, paid from the AI credits (F21.9): 429
    quota_exceeded when they are spent.
    """
    if request.type == GoalType.LIFESTYLE:
        await quota.ensure_can_talk(current_user, datetime.now(UTC))
    return await service.create(current_user.id, request)


@router.post("/check", response_model=GoalCheckResponse)
async def check_goal(
    request: GoalCheckRequest,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> GoalCheckResponse:
    """Whether a money goal is within reach, before it is saved (F23.13).

    Judged on the caller's own last three whole months (N2): doable, a stretch with
    where the money could come from, or unknown when there is too little to go on.
    Nothing is stored.
    """
    result = await GoalCheckService(session).check(
        current_user,
        request.financial_kind,
        request.target_amount,
        request.category_id,
        request.today or datetime.now(UTC).date(),
        request.target_date,
    )
    return GoalCheckResponse.model_validate(asdict(result))


@router.patch("/{goal_id}", response_model=GoalRead)
async def update_goal(
    goal_id: uuid.UUID,
    request: GoalUpdate,
    current_user: CurrentUser,
    service: Service,
    quota: Quota,
) -> Goal:
    """Change a goal; another user's is not found (N2), a broken result is 422.

    New words may map a lifestyle goal again, paid from the AI credits (F21.9).
    """
    if request.model_fields_set & {"name", "description"}:
        await quota.ensure_can_talk(current_user, datetime.now(UTC))
    return await service.update(current_user.id, goal_id, request)


@router.delete("/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_goal(goal_id: uuid.UUID, current_user: CurrentUser, service: Service) -> None:
    """Drop a goal; another user's is not found (N2)."""
    await service.delete(goal_id)
