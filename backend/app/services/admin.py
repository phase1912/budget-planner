"""Supporting accounts from the admin console (F18.6.2, F18.6.3).

Admins see facts about an account and how it is used, and help it along — confirm its
address, send it a link, give it a plan. They never read what it stored (BRD N2), never
set its password, and every action is written to the log super admins read.
"""

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.errors import DomainError, NotFoundError, ProblemCode
from app.core.config import Settings
from app.domain.activity import ActivityKind
from app.domain.admin import AdminActionKind, grant_period
from app.domain.plans import GrantedPeriod, Plan, current_plan
from app.domain.quota import CreditWallet
from app.models.activity import ActivityEvent
from app.models.admin import AdminAction, PlanGrant
from app.models.user import User
from app.ports.email import Letter
from app.repository.activity import ActivityRepository
from app.repository.admin import AdminRepository, AdminUsersRepository
from app.repository.user import UserRepository
from app.services.account import AccountService
from app.services.activity import ActivityService
from app.services.quota import QuotaService, is_admin, is_super_admin

ACTIVE_DAYS = 30
"""What "active" means in the list's filter: seen in the last 30 days."""


@dataclass(frozen=True)
class UserRow:
    user: User
    plan: Plan
    last_active_at: datetime | None


@dataclass(frozen=True)
class UserCard:
    user: User
    quota: CreditWallet
    last_active_at: datetime | None
    grants: Sequence[tuple[PlanGrant, str | None]]
    activity: Sequence[ActivityEvent]


@dataclass(frozen=True)
class LogEntry:
    action: AdminAction
    admin: str | None
    target: str | None


class AdminService:
    """The admin console's reads and support actions; callers are already checked admins."""

    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.session = session
        self.settings = settings
        self.admin = AdminRepository(session)
        self.accounts = AdminUsersRepository(session)
        self.users = UserRepository(session)

    async def users_page(
        self,
        *,
        query: str,
        confirmed: bool | None,
        paid: bool | None,
        active: bool,
        limit: int,
        offset: int,
        now: datetime,
    ) -> tuple[list[UserRow], int]:
        """Accounts matching the search and filters, newest first, and how many match."""
        found, total = await self.accounts.search(
            query=query,
            confirmed=confirmed,
            paid=paid,
            active_since=now - timedelta(days=ACTIVE_DAYS) if active else None,
            now=now,
            limit=limit,
            offset=offset,
        )
        ids = [u.id for u in found]
        seen = await self.accounts.last_active(ids)
        rows = []
        for user in found:
            plan, _ = current_plan(await self._periods(user.id), now)
            rows.append(UserRow(user, plan, seen.get(user.id)))
        return rows, total

    async def card(self, user_id: uuid.UUID, now: datetime) -> UserCard:
        """One account's facts, plan, grants and latest activity. Raises NotFoundError."""
        user = await self._target(user_id)
        grants = await self.admin.grants_of(user.id)
        granters = await self.accounts.emails(
            [g.granted_by_id for g in grants if g.granted_by_id is not None]
        )
        return UserCard(
            user=user,
            quota=await QuotaService(self.session, self.settings).quota_for(user, now),
            last_active_at=(await self.accounts.last_active([user.id])).get(user.id),
            grants=[
                (g, granters.get(g.granted_by_id) if g.granted_by_id else None) for g in grants
            ],
            activity=await ActivityRepository(self.session).recent_for(user.id),
        )

    async def confirm_email(self, admin: User, user_id: uuid.UUID) -> None:
        """Mark the account's address confirmed, as when its owner asks support to."""
        user = await self._target(user_id)
        if user.email_confirmed_at is None:
            user.email_confirmed_at = datetime.now(UTC)
            ActivityService(self.session).record(user.id, ActivityKind.EMAIL_CONFIRMED)
        self._log(admin, user, AdminActionKind.EMAIL_CONFIRMED)
        await self.session.flush()

    async def restart_onboarding(self, admin: User, user_id: uuid.UUID) -> None:
        """Show the account the first-sign-in setup again on its next visit (F23.9).

        Used to test the setup on a real account, the admin's own included: what was
        chosen there before stays as it is, only the "done" mark is taken away.
        """
        user = await self._target(user_id)
        user.onboarded_at = None
        self._log(admin, user, AdminActionKind.ONBOARDING_RESTARTED)
        await self.session.flush()

    async def confirmation_letter(self, admin: User, user_id: uuid.UUID) -> Letter:
        """A fresh confirmation letter for an unconfirmed account; DomainError if confirmed."""
        user = await self._target(user_id)
        if user.email_confirmed:
            raise DomainError(
                "This address is already confirmed.", code=ProblemCode.ALREADY_CONFIRMED
            )
        self._log(admin, user, AdminActionKind.CONFIRMATION_SENT)
        await self.session.flush()
        return AccountService(self.session).confirmation_letter(user)

    async def reset_letter(self, admin: User, user_id: uuid.UUID) -> Letter:
        """A password reset link for the account's owner; the admin never sets a password."""
        user = await self._target(user_id)
        letter = await AccountService(self.session).forgot_password(user.email, None)
        if letter is None:
            raise NotFoundError("No such account.")
        self._log(admin, user, AdminActionKind.PASSWORD_RESET_SENT)
        await self.session.flush()
        return letter

    async def grant_plan(
        self, admin: User, user_id: uuid.UUID, days: int, reason: str, now: datetime
    ) -> PlanGrant:
        """Give the paid plan for `days`, after any plan already running (F18.6.3)."""
        user = await self._target(user_id)
        _, running_until = current_plan(await self._periods(user.id), now)
        starts, ends = grant_period(days, running_until, now)
        grant = PlanGrant(
            user_id=user.id,
            plan=Plan.PAID.value,
            starts_at=starts,
            ends_at=ends,
            reason=reason.strip(),
            granted_by_id=admin.id,
        )
        self.admin.add(grant)
        await self.session.flush()
        self._log(
            admin,
            user,
            AdminActionKind.PLAN_GRANTED,
            {
                "grant_id": str(grant.id),
                "days": days,
                "ends_at": ends.isoformat(),
                "reason": reason,
            },
        )
        await self.session.flush()
        return grant

    async def revoke_grant(
        self, admin: User, user_id: uuid.UUID, grant_id: uuid.UUID, now: datetime
    ) -> None:
        """Take a grant back from now on; its row stays for the history. NotFoundError otherwise."""
        user = await self._target(user_id)
        grant = await self.admin.grant(grant_id, user.id)
        if grant is None:
            raise NotFoundError("No such grant.")
        if grant.revoked_at is None:
            grant.revoked_at = now
            self._log(admin, user, AdminActionKind.PLAN_REVOKED, {"grant_id": str(grant.id)})
        await self.session.flush()

    async def set_admin(self, super_admin: User, user_id: uuid.UUID, *, admin: bool) -> User:
        """Appoint or remove an admin; only a super admin calls this (F18.6.1).

        A super admin is one by the deployment's list, so no one changes them here:
        raises DomainError (admin_role_fixed).
        """
        user = await self._target(user_id)
        if is_super_admin(user, self.settings):
            raise DomainError(
                "A super admin is set by the deployment, not here.",
                code=ProblemCode.ADMIN_ROLE_FIXED,
            )
        if (user.role == "admin") != admin:
            user.role = "admin" if admin else "user"
            kind = AdminActionKind.ADMIN_APPOINTED if admin else AdminActionKind.ADMIN_REMOVED
            self._log(super_admin, user, kind)
        await self.session.flush()
        return user

    async def log(self, limit: int, offset: int) -> list[LogEntry]:
        """The admin log, newest first, with both sides' addresses where they still exist."""
        rows = await self.admin.log(limit, offset)
        ids = {i for r in rows for i in (r.admin_id, r.target_user_id) if i is not None}
        emails = await self.accounts.emails(list(ids))
        return [
            LogEntry(
                r,
                emails.get(r.admin_id) if r.admin_id else None,
                emails.get(r.target_user_id) if r.target_user_id else None,
            )
            for r in rows
        ]

    def is_admin(self, user: User) -> bool:
        return is_admin(user, self.settings)

    def is_super_admin(self, user: User) -> bool:
        return is_super_admin(user, self.settings)

    async def _target(self, user_id: uuid.UUID) -> User:
        user = await self.users.get(user_id)
        if user is None:
            raise NotFoundError("No such account.")
        return user

    async def _periods(self, user_id: uuid.UUID) -> list[GrantedPeriod]:
        return [
            GrantedPeriod(Plan(g.plan), g.starts_at, g.ends_at, g.revoked_at is not None)
            for g in await self.admin.grants_of(user_id)
        ]

    def _log(
        self,
        admin: User,
        user: User,
        kind: AdminActionKind,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.admin.add(
            AdminAction(
                admin_id=admin.id,
                target_user_id=user.id,
                action=kind.value,
                details=details or {},
                # The clock, not the transaction's start, so one request's actions keep order.
                created_at=datetime.now(UTC),
            )
        )
