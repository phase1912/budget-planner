"""Authentication router (F1.1.3, F1.1.4)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import AuthenticationError, RegistrationError
from app.models.user import User
from app.rate_limit import limiter
from app.schemas.auth import AuthResponse, LoginRequest, RegisterRequest
from app.schemas.user import UserResponse
from app.security import create_access_token, get_password_hash, verify_password
from app.session import get_db_session

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AuthResponse:
    """Create a new account and return it with a session (F1.1.3)."""

    # Simple check for common passwords
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

    token = create_access_token(subject=user.id)

    return AuthResponse(
        user=UserResponse.model_validate(user),
        access_token=token,
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
        # Mitigate timing attack
        from app.security import get_dummy_hash

        verify_password(login_request.password, get_dummy_hash())
        raise AuthenticationError("Invalid email or password.")

    if not verify_password(login_request.password, user.password_hash):
        raise AuthenticationError("Invalid email or password.")

    token = create_access_token(subject=user.id)

    return AuthResponse(
        user=UserResponse.model_validate(user),
        access_token=token,
    )
