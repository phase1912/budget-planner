"""User router (F1.4.1)."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.db.session import get_db_session
from app.models.user import User
from app.schemas.user import UserResponse, UserUpdateRequest
from app.services.user import UserService

router = APIRouter(prefix="/users", tags=["users"])


def get_user_service(session: Annotated[AsyncSession, Depends(get_db_session)]) -> UserService:
    return UserService(session)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: Annotated[User, Depends(get_current_user)]) -> UserResponse:
    """Read current user profile (F1.4.1)."""
    return current_user  # type: ignore[return-value]


@router.patch("/me", response_model=UserResponse)
async def update_me(
    request: UserUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[UserService, Depends(get_user_service)],
) -> UserResponse:
    """Partially update user profile (F1.4.1)."""
    updated_user = await service.update_profile(current_user, request)
    return updated_user  # type: ignore[return-value]
