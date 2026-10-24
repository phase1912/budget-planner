"""Authentication router (F1.1.3, F1.1.4, F1.2)."""

import json
from datetime import UTC, datetime
from typing import Annotated
from urllib.parse import urlencode

from fastapi import APIRouter, BackgroundTasks, Depends, Form, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import rate_limit
from app.api.dependencies import (
    get_email_guard,
    get_mailer,
    get_optional_user,
    get_sign_in_service,
)
from app.api.rate_limit import limiter
from app.core.config import get_settings
from app.db.session import get_db_session
from app.models.user import User
from app.ports.sign_in import Provider
from app.schemas.auth import (
    AppleNotification,
    AuthResponse,
    ForgotPasswordRequest,
    LinkRequest,
    LoginRequest,
    MessageResponse,
    ProviderSignInRequest,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    SecondFactorChallenge,
    SecondFactorRequest,
    SignInProviders,
)
from app.schemas.user import UserResponse
from app.services.account import AccountService, EmailAddressGuard, admin_sign_in_letter
from app.services.auth import AuthService
from app.services.mailer import Mailer
from app.services.sign_in import ProviderSignIn, SignInService

router = APIRouter(prefix="/auth", tags=["auth"])


def get_auth_service(session: Annotated[AsyncSession, Depends(get_db_session)]) -> AuthService:
    return AuthService(session)


def get_account_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AccountService:
    return AccountService(session)


Accounts = Annotated[AccountService, Depends(get_account_service)]
Mail = Annotated[Mailer, Depends(get_mailer)]
SignIn = Annotated[SignInService, Depends(get_sign_in_service)]


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
    response_model=AuthResponse | SecondFactorChallenge,
    responses={status.HTTP_429_TOO_MANY_REQUESTS: {"description": "Too Many Requests"}},
)
@limiter.limit(rate_limit.LOGIN)
async def login(
    request: Request,
    login_request: LoginRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
    mailer: Mail,
    background_tasks: BackgroundTasks,
) -> AuthResponse | SecondFactorChallenge:
    """Authenticate and return a session (F1.1.4), or ask for the authenticator code.

    An account with two-factor sign-in gets a challenge to send back with its code to
    `/auth/login/second-factor` (F18.6.1). An admin is told by letter of every sign-in.
    """
    outcome = await service.login(login_request)
    if isinstance(outcome, str):
        return SecondFactorChallenge(second_factor_token=outcome)
    user_response, access_token, refresh_token = outcome
    _tell_admin(user_response, mailer, background_tasks)
    return AuthResponse(user=user_response, access_token=access_token, refresh_token=refresh_token)


@router.post("/login/second-factor", response_model=AuthResponse)
@limiter.limit(rate_limit.LOGIN)
async def login_second_factor(
    request: Request,
    body: SecondFactorRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
    mailer: Mail,
    background_tasks: BackgroundTasks,
) -> AuthResponse:
    """Finish signing in with an authenticator or recovery code (F18.6.1); 401 if wrong."""
    user_response, access_token, refresh_token = await service.complete_second_factor(
        body.token, body.code
    )
    _tell_admin(user_response, mailer, background_tasks)
    return AuthResponse(user=user_response, access_token=access_token, refresh_token=refresh_token)


def _tell_admin(user: UserResponse, mailer: Mailer, background_tasks: BackgroundTasks) -> None:
    """Write to an admin that their account was signed in to, so a stranger's is seen."""
    if user.is_admin:
        background_tasks.add_task(mailer.deliver, admin_sign_in_letter(user, datetime.now(UTC)))


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


@router.get("/providers", response_model=SignInProviders)
async def sign_in_providers(sign_in: SignIn) -> SignInProviders:
    """Which of Google and Apple are switched on, with the web's client ids (F1.6.2)."""
    ids = sign_in.client_ids()
    return SignInProviders(google=ids["google"], apple=ids["apple"])


@router.post(
    "/oidc/{provider}",
    response_model=AuthResponse | SecondFactorChallenge,
    responses={status.HTTP_429_TOO_MANY_REQUESTS: {"description": "Too Many Requests"}},
)
@limiter.limit(rate_limit.LOGIN)
async def sign_in_with_provider(
    request: Request,
    provider: Provider,
    body: ProviderSignInRequest,
    sign_in: SignIn,
    service: Annotated[AuthService, Depends(get_auth_service)],
    current: Annotated[User | None, Depends(get_optional_user)],
    mailer: Mail,
    background_tasks: BackgroundTasks,
) -> AuthResponse | SecondFactorChallenge:
    """Sign in, or open an account, with Google's or Apple's ID token (F1.6.1).

    Signed in already, the provider is linked to that account. 404
    sign_in_provider_off, 401 id_token_invalid or provider_email_unverified, 409
    link_needs_password (send the account's password with the token again) or
    identity_taken, 400 terms_required (a new account: send accept_terms).
    """
    user, _opened = await sign_in.sign_in(
        provider, ProviderSignIn(**body.model_dump()), current=current
    )
    outcome = await service.open_session(user)
    if isinstance(outcome, str):
        return SecondFactorChallenge(second_factor_token=outcome)
    user_response, access_token, refresh_token = outcome
    _tell_admin(user_response, mailer, background_tasks)
    return AuthResponse(user=user_response, access_token=access_token, refresh_token=refresh_token)


@router.post("/apple/callback", status_code=status.HTTP_303_SEE_OTHER)
async def apple_callback(
    state: Annotated[str, Form(max_length=256)] = "",
    id_token: Annotated[str | None, Form(max_length=8192)] = None,
    code: Annotated[str | None, Form(max_length=1024)] = None,
    user: Annotated[str | None, Form(max_length=2048)] = None,
    error: Annotated[str | None, Form(max_length=256)] = None,
) -> RedirectResponse:
    """Hand Apple's web sign-in back to the client (F1.6.2).

    Apple posts its answer here (form_post, required when it shares the name); the
    client checks nothing has been swapped by its `state` and posts the token to
    `/auth/oidc/apple`. The fragment never reaches a server's logs.
    """
    fields = {"state": state}
    if error:
        fields["error"] = error
    if id_token:
        fields["id_token"] = id_token
    if code:
        fields["code"] = code
    if user:
        try:
            name = json.loads(user).get("name") or {}
        except (ValueError, AttributeError):
            name = {}
        fields["first_name"] = str(name.get("firstName") or "")[:50]
        fields["last_name"] = str(name.get("lastName") or "")[:50]
    target = f"{get_settings().link_base}/auth/callback/apple#{urlencode(fields)}"
    return RedirectResponse(target, status_code=status.HTTP_303_SEE_OTHER)


@router.post("/apple/notifications", status_code=status.HTTP_204_NO_CONTENT)
async def apple_notifications(body: AppleNotification, sign_in: SignIn) -> None:
    """Apple's server-to-server notifications (F1.6.3): consent withdrawn unlinks Apple."""
    await sign_in.apple_notification(body.payload)
