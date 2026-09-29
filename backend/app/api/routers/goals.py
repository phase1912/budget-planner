import uuid
from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.db.session import get_db_session
from app.models.goal import Goal
from app.models.user import User
from app.repository.category import CategoryRepository
from app.repository.goal import GoalRepository
from app.schemas.goal import GoalCreate, GoalRead, GoalUpdate
from app.services.goal import GoalService

router = APIRouter(prefix="/api/v1/goals", tags=["goals"])


def get_goal_service(session: Annotated[AsyncSession, Depends(get_db_session)]) -> GoalService:
    """The goal service bound to the request's session."""
    return GoalService(GoalRepository(session), CategoryRepository(session))


Service = Annotated[GoalService, Depends(get_goal_service)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.get("", response_model=list[GoalRead])
async def list_goals(current_user: CurrentUser, service: Service) -> Sequence[Goal]:
    """The caller's goals, newest first (BRD F1)."""
    return await service.list()


@router.post("", response_model=GoalRead, status_code=status.HTTP_201_CREATED)
async def create_goal(request: GoalCreate, current_user: CurrentUser, service: Service) -> Goal:
    """State a goal (BRD F1); a malformed one is refused with 422 and the reason."""
    return await service.create(current_user.id, request)


@router.patch("/{goal_id}", response_model=GoalRead)
async def update_goal(
    goal_id: uuid.UUID, request: GoalUpdate, current_user: CurrentUser, service: Service
) -> Goal:
    """Change a goal; another user's is not found (N2), a broken result is 422."""
    return await service.update(current_user.id, goal_id, request)


@router.delete("/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_goal(goal_id: uuid.UUID, current_user: CurrentUser, service: Service) -> None:
    """Drop a goal; another user's is not found (N2)."""
    await service.delete(goal_id)
