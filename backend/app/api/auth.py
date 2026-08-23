"""Authentication router (F1.1.3, F1.1.4, F1.2)."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.errors import AuthenticationError, RegistrationError
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.rate_limit import limiter
from app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    MessageResponse,
    RefreshRequest,
    RegisterRequest,
)
from app.schemas.user import UserResponse
from app.security import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
    verify_password,
)
from app.session import get_db_session

router = APIRouter(prefix="/auth", tags=["auth"])


async def _create_session(user_id: uuid.UUID, session: AsyncSession) -> tuple[str, str]:
    """Helper to create access and refresh tokens, and persist the refresh token."""
    access_token = create_access_token(subject=user_id)
    refresh_token_str = create_refresh_token()
    family_id = uuid.uuid4()

    settings = get_settings()
    expires_at = datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)

    rt = RefreshToken(
        user_id=user_id,
        token=refresh_token_str,
        family_id=family_id,
        expires_at=expires_at,
    )
    session.add(rt)
    await session.flush()

    return access_token, refresh_token_str


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AuthResponse:
    """Create a new account and return it with a session (F1.1.3)."""
    common_passwords = {"password", "12345678", "qwertyui", "admin123", "password123"}
    if request.password.lower() in common_passwords or len(request.password) < 8:
        raise RegistrationError("Registration failed. Please check your details and try again.")

    stmt = select(User).where(User.email == request.email)
    existing_user = (await session.execute(stmt)).scalar_one_or_none()
    if existing_user:
        raise RegistrationError("Registration failed. Please check your details and try again.")

    hashed_password = get_password_hash(request.password)
    user = User(
        email=request.email,
        password_hash=hashed_password,
        first_name=request.first_name,
        last_name=request.last_name,
    )
    session.add(user)
    try:
        await session.flush()
    except IntegrityError as err:
        await session.rollback()
        raise RegistrationError(
            "Registration failed. Please check your details and try again."
        ) from err

    access_token, refresh_token = await _create_session(user.id, session)

    return AuthResponse(
        user=UserResponse.model_validate(user),
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post(
    "/login",
    response_model=AuthResponse,
    responses={status.HTTP_429_TOO_MANY_REQUESTS: {"description": "Too Many Requests"}},
)
@limiter.limit("5/minute")
async def login(
    request: Request,
    login_request: LoginRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AuthResponse:
    """Authenticate and return an access token (F1.1.4)."""
    stmt = select(User).where(User.email == login_request.email)
    user = (await session.execute(stmt)).scalar_one_or_none()

    if not user:
        from app.security import get_dummy_hash

        verify_password(login_request.password, get_dummy_hash())
        raise AuthenticationError("Invalid email or password.")

    if not verify_password(login_request.password, user.password_hash):
        raise AuthenticationError("Invalid email or password.")

    access_token, refresh_token = await _create_session(user.id, session)

    return AuthResponse(
        user=UserResponse.model_validate(user),
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/refresh", response_model=AuthResponse)
async def refresh(
    request: RefreshRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AuthResponse:
    """Exchange a valid refresh token for a new session (F1.2.3)."""
    stmt = select(RefreshToken).where(RefreshToken.token == request.refresh_token)
    rt = (await session.execute(stmt)).scalar_one_or_none()

    if not rt:
        raise AuthenticationError("Invalid refresh token.")

    now = datetime.now(UTC)

    # Reuse detection
    if rt.is_used or rt.revoked_at or rt.expires_at < now:
        # Revoke whole family
        if rt.family_id:
            revoke_stmt = (
                update(RefreshToken)
                .where(RefreshToken.family_id == rt.family_id)
                .values(revoked_at=now)
            )
            await session.execute(revoke_stmt)
            await session.flush()
        raise AuthenticationError("Session expired. Please log in again.")

    # Mark current token as used
    rt.is_used = True
    rt.revoked_at = now

    # Get user
    user_stmt = select(User).where(User.id == rt.user_id)
    user = (await session.execute(user_stmt)).scalar_one_or_none()
    if not user:
        raise AuthenticationError("User not found.")

    # Issue new token pair in the same family
    access_token = create_access_token(subject=user.id)
    new_refresh_token_str = create_refresh_token()
    settings = get_settings()
    expires_at = now + timedelta(days=settings.refresh_token_expire_days)

    new_rt = RefreshToken(
        user_id=user.id,
        token=new_refresh_token_str,
        family_id=rt.family_id,
        expires_at=expires_at,
    )
    session.add(new_rt)
    await session.flush()

    return AuthResponse(
        user=UserResponse.model_validate(user),
        access_token=access_token,
        refresh_token=new_refresh_token_str,
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(
    request: RefreshRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> MessageResponse:
    """Revoke the given session (F1.2.3)."""
    stmt = select(RefreshToken).where(RefreshToken.token == request.refresh_token)
    rt = (await session.execute(stmt)).scalar_one_or_none()

    if rt:
        now = datetime.now(UTC)
        rt.revoked_at = now
        rt.is_used = True
        await session.flush()

    return MessageResponse(message="Logged out successfully.")
