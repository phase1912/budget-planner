"""Authentication router (F1.1.3, F1.1.4, F1.2)."""

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import rate_limit
from app.api.dependencies import get_email_guard, get_mailer
from app.api.rate_limit import limiter
from app.db.session import get_db_session
from app.schemas.auth import (
    AuthResponse,
    ForgotPasswordRequest,
    LinkRequest,
    LoginRequest,
    MessageResponse,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
)
from app.schemas.user import UserResponse
from app.services.account import AccountService, EmailAddressGuard
from app.services.auth import AuthService
from app.services.mailer import Mailer

router = APIRouter(prefix="/auth", tags=["auth"])


def get_auth_service(session: Annotated[AsyncSession, Depends(get_db_session)]) -> AuthService:
    return AuthService(session)


def get_account_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AccountService:
    return AccountService(session)


Accounts = Annotated[AccountService, Depends(get_account_service)]
Mail = Annotated[Mailer, Depends(get_mailer)]


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(rate_limit.REGISTER)
async def register(
    request: Request,
    register_request: RegisterRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
    guard: Annotated[EmailAddressGuard, Depends(get_email_guard)],
    accounts: Accounts,
    mailer: Mail,
    background_tasks: BackgroundTasks,
) -> AuthResponse:
    """Create a new account, send its confirmation letter, return it with a session (F1.1.3).

    Limited per client IP (F10.6.3), so accounts cannot be made in bulk to get round
    the per-account receipt quota. Throwaway and undeliverable addresses are refused
    (F17.8.4); the account can look around but not upload until confirmed (F17.8.2).
    """
    user_response, access_token, refresh_token = await service.register(register_request, guard)
    letter = await accounts.confirmation_letter_for(user_response.id, register_request.language)
    if letter is not None:
        background_tasks.add_task(mailer.deliver, letter)
    return AuthResponse(user=user_response, access_token=access_token, refresh_token=refresh_token)


@router.post(
    "/login",
    response_model=AuthResponse,
    responses={status.HTTP_429_TOO_MANY_REQUESTS: {"description": "Too Many Requests"}},
)
@limiter.limit(rate_limit.LOGIN)
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


@router.post("/confirm-email", response_model=UserResponse)
async def confirm_email(request: LinkRequest, accounts: Accounts) -> UserResponse:
    """Confirm the address a confirmation link was sent to (F17.8.2).

    Needs no session: the link may be opened on another device. 400 link_invalid for
    an expired link or one sent to an address the account no longer uses.
    """
    user = await accounts.confirm_email(request.token)
    return UserResponse.model_validate(user)


@router.post(
    "/password/forgot", response_model=MessageResponse, status_code=status.HTTP_202_ACCEPTED
)
@limiter.limit(rate_limit.ACCOUNT_LETTER)
async def forgot_password(
    request: Request,
    body: ForgotPasswordRequest,
    accounts: Accounts,
    mailer: Mail,
    background_tasks: BackgroundTasks,
) -> MessageResponse:
    """Send a password reset link, if the address has an account (F17.8.3).

    Answers the same whether it has or not, so the form cannot be used to learn which
    addresses have accounts (G2).
    """
    letter = await accounts.forgot_password(body.email, body.language)
    if letter is not None:
        background_tasks.add_task(mailer.deliver, letter)
    return MessageResponse(message="If the address has an account, a reset link is on its way.")


@router.post("/password/reset", response_model=MessageResponse)
@limiter.limit(rate_limit.LOGIN)
async def reset_password(
    request: Request, body: ResetPasswordRequest, accounts: Accounts
) -> MessageResponse:
    """Set a new password from a reset link; every session of the account ends (F17.8.3)."""
    await accounts.reset_password(body.token, body.password)
    return MessageResponse(message="The password is changed. Sign in with the new one.")


@router.post("/email/confirm-change", response_model=UserResponse)
async def confirm_email_change(
    request: LinkRequest,
    accounts: Accounts,
    mailer: Mail,
    background_tasks: BackgroundTasks,
) -> UserResponse:
    """Switch the account to the address the link was sent to, telling the old one (F17.8.3)."""
    user, notice = await accounts.confirm_email_change(request.token)
    background_tasks.add_task(mailer.deliver, notice)
    return UserResponse.model_validate(user)
