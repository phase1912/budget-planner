"""User router (F1.4.1)."""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_quota_service
from app.db.session import get_db_session
from app.models.user import User
from app.schemas.user import ReceiptQuotaRead, UserResponse, UserUpdateRequest
from app.services.quota import QuotaService
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


@router.post("/me/forwarding-address/regenerate", response_model=UserResponse)
async def regenerate_forwarding_address(
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[UserService, Depends(get_user_service)],
) -> UserResponse:
    """Replace the user's receipt forwarding address; the old one stops working (F11.2)."""
    updated_user = await service.regenerate_forwarding_address(current_user)
    return updated_user  # type: ignore[return-value]


@router.get("/me/quota", response_model=ReceiptQuotaRead)
async def get_my_quota(
    current_user: Annotated[User, Depends(get_current_user)],
    quotas: Annotated[QuotaService, Depends(get_quota_service)],
) -> ReceiptQuotaRead:
    """How many receipts the user may still have read this month (F10.6.1)."""
    quota = await quotas.quota_for(current_user, datetime.now(UTC))
    return ReceiptQuotaRead.model_validate(quota)
