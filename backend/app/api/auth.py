"""Authentication router (F1.1.3, F1.1.4, F1.2)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.rate_limit import limiter
from app.db.session import get_db_session
from app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    MessageResponse,
    RefreshRequest,
    RegisterRequest,
)
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


def get_auth_service(session: Annotated[AsyncSession, Depends(get_db_session)]) -> AuthService:
    return AuthService(session)


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> AuthResponse:
    """Create a new account and return it with a session (F1.1.3)."""
    user_response, access_token, refresh_token = await service.register(request)
    return AuthResponse(user=user_response, access_token=access_token, refresh_token=refresh_token)


@router.post(
    "/login",
    response_model=AuthResponse,
    responses={status.HTTP_429_TOO_MANY_REQUESTS: {"description": "Too Many Requests"}},
)
@limiter.limit("5/minute")
async def login(
    request: Request,
    login_request: LoginRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> AuthResponse:
    """Authenticate and return an access token (F1.1.4)."""
    user_response, access_token, refresh_token = await service.login(login_request)
    return AuthResponse(user=user_response, access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=AuthResponse)
async def refresh(
    request: RefreshRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> AuthResponse:
    """Exchange a valid refresh token for a new session (F1.2.3)."""
    user_response, access_token, new_refresh_token = await service.refresh(request)
    return AuthResponse(
        user=user_response,
        access_token=access_token,
        refresh_token=new_refresh_token,
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(
    request: RefreshRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> MessageResponse:
    """Revoke the given session (F1.2.3)."""
    await service.logout(request)
    return MessageResponse(message="Logged out successfully.")
