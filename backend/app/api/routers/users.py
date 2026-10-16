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
)
from app.api.rate_limit import limiter
from app.db.session import get_db_session
from app.models.user import User
from app.schemas.auth import MessageResponse
from app.schemas.user import (
    AccountDeletionRequest,
    EmailChangeRequest,
    ReceiptQuotaRead,
    UserResponse,
    UserUpdateRequest,
)
from app.services.account import AccountService, EmailAddressGuard
from app.services.account_closure import AccountClosureService
from app.services.mailer import Mailer
from app.services.quota import QuotaService
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
) -> None:
    """Delete the account and everything held about its owner (F17.9.1, GDPR art. 17).

    403 invalid_credentials for a wrong password. The photos and exports are removed
    from storage after the response; signing in fails from now on.
    """
    prefixes = await AccountClosureService(session).close(current_user, body.password)
    background_tasks.add_task(_remove_files, prefixes)
