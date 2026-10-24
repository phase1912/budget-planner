"""User router (F1.4.1)."""

import logging
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.storage_factory import configured_storage
from app.api import rate_limit
from app.api.dependencies import (
    get_current_user,
    get_email_guard,
    get_mailer,
    get_quota_service,
    get_sign_in_service,
)
from app.api.rate_limit import limiter
from app.db.session import get_db_session
from app.models.user import User
from app.ports.sign_in import Provider
from app.schemas.auth import LinkedIdentityRead, MessageResponse
from app.schemas.user import (
    AccountDeletionRequest,
    AiConsentRequest,
    EmailChangeRequest,
    ReceiptQuotaRead,
    TwoFactorCodeRequest,
    TwoFactorEnabledRead,
    TwoFactorOffRequest,
    TwoFactorSetupRead,
    UserResponse,
    UserUpdateRequest,
)
from app.services.account import AccountService, EmailAddressGuard
from app.services.account_closure import AccountClosureService
from app.services.auth import AuthService
from app.services.mailer import Mailer
from app.services.quota import QuotaService
from app.services.sign_in import SignInService
from app.services.two_factor import TwoFactorService
from app.services.user import UserService

router = APIRouter(prefix="/users", tags=["users"])
logger = logging.getLogger(__name__)


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


@router.put("/me/ai-consent", response_model=UserResponse)
async def set_ai_consent(
    request: AiConsentRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[UserService, Depends(get_user_service)],
) -> UserResponse:
    """Allow the AI to read the caller's receipts, words and recordings, or withdraw it
    (F25.3.2); withdrawn, every AI feature waits until it is allowed again."""
    updated_user = await service.set_ai_consent(current_user, given=request.given)
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
    """What is left of the user's AI credits this month, as receipts and messages (F21.9)."""
    return ReceiptQuotaRead.of(await quotas.quota_for(current_user, datetime.now(UTC)))


@router.post(
    "/me/confirmation/resend",
    response_model=MessageResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
@limiter.limit(rate_limit.ACCOUNT_LETTER)
async def resend_confirmation(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    mailer: Annotated[Mailer, Depends(get_mailer)],
    background_tasks: BackgroundTasks,
) -> MessageResponse:
    """Send the confirmation link again, unless the address is confirmed already (F17.8.2)."""
    if not current_user.email_confirmed:
        letter = AccountService(session).confirmation_letter(current_user)
        background_tasks.add_task(mailer.deliver, letter)
    return MessageResponse(message="A confirmation link is on its way.")


@router.post("/me/email", response_model=MessageResponse, status_code=status.HTTP_202_ACCEPTED)
@limiter.limit(rate_limit.ACCOUNT_LETTER)
async def change_email(
    request: Request,
    body: EmailChangeRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    guard: Annotated[EmailAddressGuard, Depends(get_email_guard)],
    mailer: Annotated[Mailer, Depends(get_mailer)],
    background_tasks: BackgroundTasks,
) -> MessageResponse:
    """Send a link to the new address; the account switches only once it is followed.

    403 invalid_credentials for a wrong password; 400 email_taken, disposable_email or
    email_domain_unreachable for an address the account cannot move to (F17.8.3-4).
    """
    letter = await AccountService(session).request_email_change(
        current_user, body.email, body.password, guard
    )
    background_tasks.add_task(mailer.deliver, letter)
    return MessageResponse(message="A link to confirm the new address is on its way.")


async def _remove_files(prefixes: list[str]) -> None:
    """Remove a deleted account's files; a failure is logged, and lifecycle rules clean up."""
    try:
        async with configured_storage() as storage:
            for prefix in prefixes:
                await storage.delete_prefix(prefix)
    except Exception:
        logger.exception("Files of a deleted account were not all removed")


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(rate_limit.LOGIN)
async def delete_me(
    request: Request,
    body: AccountDeletionRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    background_tasks: BackgroundTasks,
    sign_in: Annotated[SignInService, Depends(get_sign_in_service)],
) -> None:
    """Delete the account and everything held about its owner (F17.9.1, GDPR art. 17).

    403 invalid_credentials for a wrong password (or, for an account without one, the
    wrong address). Apple's tokens are revoked first (F1.6.3). The photos and exports
    are removed from storage after the response; signing in fails from now on.
    """
    prefixes = await AccountClosureService(session, sign_in.revoke_all).close(
        current_user, body.password
    )
    background_tasks.add_task(_remove_files, prefixes)


@router.post("/me/two-factor/setup", response_model=TwoFactorSetupRead)
async def begin_two_factor(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> TwoFactorSetupRead:
    """Start setting up an authenticator: a QR code, not in force until confirmed (F18.6.1)."""
    setup = await TwoFactorService(session).begin(current_user)
    return TwoFactorSetupRead(secret=setup.secret, uri=setup.uri, qr_svg=setup.qr_svg)


@router.post("/me/two-factor/confirm", response_model=TwoFactorEnabledRead)
@limiter.limit(rate_limit.LOGIN)
async def confirm_two_factor(
    request: Request,
    body: TwoFactorCodeRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> TwoFactorEnabledRead:
    """Turn it on with a first code; the recovery codes come back once, with a session
    that has the second factor, so an admin need not sign in again (F18.6.1)."""
    codes = await TwoFactorService(session).confirm(current_user, body.code)
    access_token, refresh_token = await AuthService(session).upgrade_to_second_factor(current_user)
    return TwoFactorEnabledRead(
        recovery_codes=codes, access_token=access_token, refresh_token=refresh_token
    )


@router.post("/me/two-factor/disable", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(rate_limit.LOGIN)
async def disable_two_factor(
    request: Request,
    body: TwoFactorOffRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> None:
    """Turn it off with the password and a code (F18.6.1); 403 if either is wrong."""
    await TwoFactorService(session).turn_off(current_user, body.password, body.code)


@router.get("/me/identities", response_model=list[LinkedIdentityRead])
async def list_identities(
    current_user: Annotated[User, Depends(get_current_user)],
    sign_in: Annotated[SignInService, Depends(get_sign_in_service)],
) -> list[LinkedIdentityRead]:
    """The providers that sign in to the account (F1.6.2)."""
    return [LinkedIdentityRead.model_validate(i) for i in await sign_in.identities(current_user)]


@router.delete("/me/identities/{provider}", status_code=status.HTTP_204_NO_CONTENT)
async def unlink_identity(
    provider: Provider,
    current_user: Annotated[User, Depends(get_current_user)],
    sign_in: Annotated[SignInService, Depends(get_sign_in_service)],
) -> None:
    """Stop a provider signing in; 409 last_way_in while it is the only way in (F1.6.2)."""
    await sign_in.unlink(current_user, provider)
