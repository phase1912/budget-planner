"""The admin console (F18.6): accounts, support actions, plan grants and the admin log.

Every route needs an admin signed in with a second factor (`get_admin_user`); appointing
admins and reading the log need a super admin. Nothing here returns a receipt (BRD N2).
"""

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_admin_user, get_mailer, get_super_admin
from app.core.config import get_settings
from app.db.session import get_db_session
from app.models.user import User
from app.schemas.admin import (
    ActivityRead,
    AdminActionRead,
    AdminLogPage,
    AdminRoleRequest,
    AdminUserCard,
    AdminUserRow,
    AdminUsersPage,
    PlanGrantRead,
    PlanGrantRequest,
)
from app.services.admin import AdminService
from app.services.mailer import Mailer

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

Admin = Annotated[User, Depends(get_admin_user)]
SuperAdmin = Annotated[User, Depends(get_super_admin)]
Session = Annotated[AsyncSession, Depends(get_db_session)]
Mail = Annotated[Mailer, Depends(get_mailer)]


def _service(session: AsyncSession) -> AdminService:
    return AdminService(session, get_settings())


@router.get("/users", response_model=AdminUsersPage)
async def list_users(
    _admin: Admin,
    session: Session,
    q: Annotated[str, Query(max_length=100)] = "",
    confirmed: bool | None = None,
    paid: bool | None = None,
    active: bool = False,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> AdminUsersPage:
    """Accounts by address, with filters: confirmed, on a paid plan, active in 30 days."""
    service = _service(session)
    rows, total = await service.users_page(
        query=q,
        confirmed=confirmed,
        paid=paid,
        active=active,
        limit=limit,
        offset=offset,
        now=datetime.now(UTC),
    )
    return AdminUsersPage(
        items=[
            AdminUserRow(
                id=r.user.id,
                email=r.user.email,
                first_name=r.user.first_name,
                last_name=r.user.last_name,
                created_at=r.user.created_at,
                email_confirmed=r.user.email_confirmed,
                is_admin=service.is_admin(r.user),
                plan=r.plan.value,
                last_active_at=r.last_active_at,
            )
            for r in rows
        ],
        total=total,
    )


@router.get("/users/{user_id}", response_model=AdminUserCard)
async def user_card(user_id: uuid.UUID, _admin: Admin, session: Session) -> AdminUserCard:
    """One account's facts, plan, grants and latest activity; 404 for none."""
    service = _service(session)
    card = await service.card(user_id, datetime.now(UTC))
    user = card.user
    return AdminUserCard(
        id=user.id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        created_at=user.created_at,
        email_confirmed_at=user.email_confirmed_at,
        onboarded_at=user.onboarded_at,
        language=user.language,
        terms_version=user.terms_version,
        is_admin=service.is_admin(user),
        is_super_admin=service.is_super_admin(user),
        two_factor_enabled=user.two_factor_enabled,
        plan=card.quota.plan,
        plan_ends_on=card.quota.plan_ends_on,
        receipts_limit=card.quota.limit,
        receipts_used=card.quota.used,
        last_active_at=card.last_active_at,
        grants=[
            PlanGrantRead(
                id=g.id,
                plan=g.plan,
                starts_at=g.starts_at,
                ends_at=g.ends_at,
                reason=g.reason,
                granted_by=by,
                revoked_at=g.revoked_at,
                created_at=g.created_at,
            )
            for g, by in card.grants
        ],
        activity=[ActivityRead(event=e.event, created_at=e.created_at) for e in card.activity],
    )


@router.post("/users/{user_id}/confirm-email", status_code=status.HTTP_204_NO_CONTENT)
async def confirm_email(user_id: uuid.UUID, admin: Admin, session: Session) -> Response:
    """Mark the account's address confirmed (F18.6.2)."""
    await _service(session).confirm_email(admin, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/users/{user_id}/restart-onboarding", status_code=status.HTTP_204_NO_CONTENT)
async def restart_onboarding(user_id: uuid.UUID, admin: Admin, session: Session) -> Response:
    """Show the account the first-sign-in setup again on its next visit (F23.9)."""
    await _service(session).restart_onboarding(admin, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/users/{user_id}/send-confirmation", status_code=status.HTTP_204_NO_CONTENT)
async def send_confirmation(
    user_id: uuid.UUID,
    admin: Admin,
    session: Session,
    mailer: Mail,
    background_tasks: BackgroundTasks,
) -> Response:
    """Send the account a fresh confirmation link; 409 already_confirmed if it needs none."""
    letter = await _service(session).confirmation_letter(admin, user_id)
    background_tasks.add_task(mailer.deliver, letter)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/users/{user_id}/send-password-reset", status_code=status.HTTP_204_NO_CONTENT)
async def send_password_reset(
    user_id: uuid.UUID,
    admin: Admin,
    session: Session,
    mailer: Mail,
    background_tasks: BackgroundTasks,
) -> Response:
    """Send the account's owner a reset link; an admin never sets a password (F18.6.2)."""
    letter = await _service(session).reset_letter(admin, user_id)
    background_tasks.add_task(mailer.deliver, letter)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/users/{user_id}/grants", status_code=status.HTTP_201_CREATED)
async def grant_plan(
    user_id: uuid.UUID, body: PlanGrantRequest, admin: Admin, session: Session
) -> PlanGrantRead:
    """Give the paid plan for some days, after any plan running now (F18.6.3)."""
    grant = await _service(session).grant_plan(
        admin, user_id, body.days, body.reason, datetime.now(UTC)
    )
    return PlanGrantRead(
        id=grant.id,
        plan=grant.plan,
        starts_at=grant.starts_at,
        ends_at=grant.ends_at,
        reason=grant.reason,
        granted_by=admin.email,
        revoked_at=None,
        created_at=grant.created_at,
    )


@router.post("/users/{user_id}/grants/{grant_id}/revoke", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_grant(
    user_id: uuid.UUID, grant_id: uuid.UUID, admin: Admin, session: Session
) -> Response:
    """Take a grant back from now; 404 for a grant not this account's."""
    await _service(session).revoke_grant(admin, user_id, grant_id, datetime.now(UTC))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/users/{user_id}/role", status_code=status.HTTP_204_NO_CONTENT)
async def set_role(
    user_id: uuid.UUID, body: AdminRoleRequest, super_admin: SuperAdmin, session: Session
) -> Response:
    """Appoint or remove an admin: super admins only (F18.6.1)."""
    await _service(session).set_admin(super_admin, user_id, admin=body.admin)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/log", response_model=AdminLogPage)
async def admin_log(
    _super_admin: SuperAdmin,
    session: Session,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> AdminLogPage:
    """What admins did, newest first: super admins only (F18.6.3)."""
    entries = await _service(session).log(limit, offset)
    return AdminLogPage(
        items=[
            AdminActionRead(
                id=e.action.id,
                created_at=e.action.created_at,
                action=e.action.action,
                admin=e.admin,
                target=e.target,
                details=e.action.details,
            )
            for e in entries
        ]
    )
