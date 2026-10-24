"""The admin console by chat (F21.12, F18.6, ADR-0029).

Offered only to an admin whose session was opened with a second factor — appointing
admins only to a super admin — and checked again when a card is saved. Every action goes
through the console's own service, so it lands in the admin log as from the console. No
tool here reads another user's receipts, incomes or balances (N2): only account facts and
usage, as the console shows them.
"""

import json
from datetime import UTC, date, datetime, timedelta
from typing import Any

from pydantic import BaseModel, EmailStr, Field

from app.api.errors import DomainError, NotFoundError, ProblemCode
from app.assistant.tools.base import Answer, FormField, Reader, ToolContext, Writer, as_id
from app.core.config import get_settings
from app.domain.periods import DateRange
from app.models.user import User
from app.repository.user import UserRepository
from app.services.activity import UsageReportService
from app.services.admin import AdminService

FOUND = 10
"""How many accounts one search answers with."""
LISTED = 15
"""How many reports or log entries one answer holds, newest first."""


def _service(ctx: ToolContext) -> AdminService:
    return AdminService(ctx.session, get_settings())


async def _account(ctx: ToolContext, email: str) -> User | None:
    return await UserRepository(ctx.session).get_by_email(email.strip().lower())


class FindArgs(BaseModel):
    """Part of an account's address or name."""

    query: str = Field(min_length=1, max_length=120)


class FindUsers(Reader):
    """Accounts matching a search, as the console's list shows them (F18.6.2)."""

    name = "admin_find_users"
    description = "Admin only: accounts whose address or name holds the search, newest first."
    args = FindArgs
    needs = "admin"

    async def read(self, ctx: ToolContext, args: FindArgs) -> Answer:
        rows, total = await _service(ctx).users_page(
            query=args.query,
            confirmed=None,
            paid=None,
            active=False,
            limit=FOUND,
            offset=0,
            now=datetime.now(UTC),
        )
        found = [
            {
                "email": r.user.email,
                "name": f"{r.user.first_name} {r.user.last_name}".strip(),
                "plan": r.plan.value,
                "confirmed": r.user.email_confirmed_at is not None,
                "last_active": r.last_active_at.date().isoformat() if r.last_active_at else None,
            }
            for r in rows
        ]
        return Answer(json.dumps({"matching": total, "accounts": found}))


class AccountArgs(BaseModel):
    """An account, by its address."""

    email: EmailStr


class AccountFacts(Reader):
    """One account's facts and usage as the console's card shows them — never its money."""

    name = "admin_account"
    description = (
        "Admin only: one account's facts — created, confirmed, plan and until when, AI credits "
        "used and left this month, last active. Never its receipts or money."
    )
    args = AccountArgs
    needs = "admin"

    async def read(self, ctx: ToolContext, args: AccountArgs) -> Answer:
        user = await _account(ctx, args.email)
        if user is None:
            return Answer(json.dumps({"error": "no account with that address"}))
        card = await _service(ctx).card(user.id, datetime.now(UTC))
        wallet = card.quota
        facts = {
            "email": user.email,
            "created": user.created_at.date().isoformat(),
            "confirmed": user.email_confirmed_at is not None,
            "plan": wallet.plan,
            "plan_ends_on": wallet.plan_ends_on.isoformat() if wallet.plan_ends_on else None,
            "credits_used": str(wallet.used),
            "credits_left": str(wallet.remaining) if wallet.remaining is not None else None,
            "last_active": card.last_active_at.date().isoformat() if card.last_active_at else None,
            "admin": _service(ctx).is_admin(user),
        }
        return Answer(json.dumps(facts))


class AccountCard(BaseModel):
    """An action on one account, as the admin approves it."""

    target: str
    user_id: str


async def _target(ctx: ToolContext, email: str) -> dict[str, Any]:
    user = await _account(ctx, email)
    if user is None:
        raise NotFoundError("No account with that address.")
    return {"target": user.email, "user_id": str(user.id)}


async def _missing(ctx: ToolContext, email: str) -> str | None:
    return None if await _account(ctx, email) is not None else "no account with that address"


class ConfirmAddress(Writer):
    """A card marking an account's address confirmed (F18.6.2)."""

    name = "admin_confirm_email"
    description = "Admin only: propose marking an account's address as confirmed."
    args = AccountArgs
    card_kind = "admin_confirm_email"
    card = AccountCard
    form = (FormField("target", "target"),)
    needs = "admin"

    async def check(self, ctx: ToolContext, args: AccountArgs) -> str | None:
        return await _missing(ctx, args.email)

    async def propose(self, ctx: ToolContext, args: AccountArgs) -> dict[str, Any]:
        return await _target(ctx, args.email)

    async def save(self, ctx: ToolContext, fields: AccountCard) -> str:
        await _service(ctx).confirm_email(ctx.user, as_id(fields.user_id))
        return f"user:{fields.user_id}"


class LetterArgs(AccountArgs):
    """An account and the letter to send it."""

    letter: str = Field(description="confirmation, or password_reset")


class LetterCard(AccountCard):
    """A letter to send, as the admin approves it."""

    letter: str


class SendLetter(Writer):
    """A card sending an account a fresh confirmation link or a password reset link; an
    admin never sets a password (F18.6.2)."""

    name = "admin_send_letter"
    description = (
        "Admin only: propose sending an account a fresh confirmation link (letter "
        "confirmation) or a password reset link (letter password_reset)."
    )
    args = LetterArgs
    card_kind = "admin_letter"
    card = LetterCard
    form = (
        FormField("target", "target"),
        FormField("letter", "choice", options=("confirmation", "password_reset")),
    )
    needs = "admin"

    async def check(self, ctx: ToolContext, args: LetterArgs) -> str | None:
        if args.letter not in ("confirmation", "password_reset"):
            return "letter is confirmation or password_reset"
        return await _missing(ctx, args.email)

    async def propose(self, ctx: ToolContext, args: LetterArgs) -> dict[str, Any]:
        return {**await _target(ctx, args.email), "letter": args.letter}

    async def save(self, ctx: ToolContext, fields: LetterCard) -> str:
        service = _service(ctx)
        user_id = as_id(fields.user_id)
        letter = (
            await service.reset_letter(ctx.user, user_id)
            if fields.letter == "password_reset"
            else await service.confirmation_letter(ctx.user, user_id)
        )
        if ctx.mailer is None or not await ctx.mailer.deliver(letter):
            raise DomainError(
                "The letter could not be sent just now.", code=ProblemCode.INVALID_CARD
            )
        return f"user:{fields.user_id}"


class GrantArgs(AccountArgs):
    """The paid plan for an account until a day, and why."""

    until: date = Field(description="YYYY-MM-DD, the plan's last day")
    reason: str = Field(min_length=1, max_length=200, description="Why, for the admin log")


class GrantCard(AccountCard):
    """A grant as the admin approves it."""

    until: date
    reason: str = Field(min_length=1, max_length=200)


class GrantPlan(Writer):
    """A card giving an account the paid plan until a day, after any plan already running,
    recorded with its reason (F18.6.3)."""

    name = "admin_grant_plan"
    description = "Admin only: propose giving an account the paid plan until a day, with why."
    args = GrantArgs
    card_kind = "admin_grant"
    card = GrantCard
    form = (
        FormField("target", "target"),
        FormField("until", "date"),
        FormField("reason", "text"),
    )
    needs = "admin"

    async def check(self, ctx: ToolContext, args: GrantArgs) -> str | None:
        if args.until < ctx.today:
            return "the plan cannot end before today"
        return await _missing(ctx, args.email)

    async def propose(self, ctx: ToolContext, args: GrantArgs) -> dict[str, Any]:
        return {
            **await _target(ctx, args.email),
            "until": args.until.isoformat(),
            "reason": args.reason,
        }

    async def save(self, ctx: ToolContext, fields: GrantCard) -> str:
        days = (fields.until - ctx.today).days + 1
        grant = await _service(ctx).grant_plan(
            ctx.user, as_id(fields.user_id), days, fields.reason, datetime.now(UTC)
        )
        return f"grant:{grant.id}"


class RevokePlan(Writer):
    """A card taking back an account's running grants from now (F18.6.3)."""

    name = "admin_revoke_plan"
    description = "Admin only: propose taking back the paid plan an account was given."
    args = AccountArgs
    card_kind = "admin_revoke"
    card = AccountCard
    form = (FormField("target", "target"),)
    needs = "admin"

    async def check(self, ctx: ToolContext, args: AccountArgs) -> str | None:
        return await _missing(ctx, args.email)

    async def propose(self, ctx: ToolContext, args: AccountArgs) -> dict[str, Any]:
        return await _target(ctx, args.email)

    async def save(self, ctx: ToolContext, fields: AccountCard) -> str:
        service = _service(ctx)
        user_id = as_id(fields.user_id)
        now = datetime.now(UTC)
        card = await service.card(user_id, now)
        for grant, _ in card.grants:
            if grant.revoked_at is None and grant.ends_at > now:
                await service.revoke_grant(ctx.user, user_id, grant.id, now)
        return f"user:{fields.user_id}"


class RoleArgs(AccountArgs):
    """An account to make an admin, or no longer one."""

    admin: bool


class RoleCard(AccountCard):
    """An admin appointed or removed, as the super admin approves it."""

    admin: bool


class SetAdmin(Writer):
    """A card appointing or removing an admin; super admins only (F18.6.1)."""

    name = "admin_set_admin"
    description = "Super admin only: propose making an account an admin, or no longer one."
    args = RoleArgs
    card_kind = "admin_role"
    card = RoleCard
    form = (FormField("target", "target"), FormField("admin", "switch"))
    needs = "super_admin"

    async def check(self, ctx: ToolContext, args: RoleArgs) -> str | None:
        return await _missing(ctx, args.email)

    async def propose(self, ctx: ToolContext, args: RoleArgs) -> dict[str, Any]:
        return {**await _target(ctx, args.email), "admin": args.admin}

    async def save(self, ctx: ToolContext, fields: RoleCard) -> str:
        await _service(ctx).set_admin(ctx.user, as_id(fields.user_id), admin=fields.admin)
        return f"user:{fields.user_id}"


class NoArgs(BaseModel):
    """Nothing to choose: the newest come first."""


class OverviewArgs(BaseModel):
    """The days the figures cover; the last seven when none are named."""

    start: date | None = Field(default=None, description="First day, YYYY-MM-DD")
    end: date | None = Field(default=None, description="Last day, YYYY-MM-DD; today if none")


class Overview(Reader):
    """The admin dashboard's figures for a period, as the console shows them (F17.3.3)."""

    name = "admin_overview"
    description = (
        "Admin only: how the service is doing over a period — visits and their sources, "
        "platforms and systems, sign-ups, confirmations, users with a receipt, uploads, "
        "receipts read, active this week and month, returning users. Counts only. Use for "
        "'what is happening in the admin console' or 'how is the service doing'."
    )
    args = OverviewArgs
    needs = "admin"

    async def read(self, ctx: ToolContext, args: OverviewArgs) -> Answer:
        end = args.end or datetime.now(UTC).date()
        start = args.start or end - timedelta(days=6)
        if start > end:
            return Answer(json.dumps({"error": "the first day is after the last"}))
        report = await UsageReportService(ctx.session, get_settings().admin_emails).report(
            DateRange(start, end)
        )
        figures = {
            "from": start.isoformat(),
            "to": end.isoformat(),
            "visits": report.visits,
            "page_views": report.page_views,
            "visits_by_source": dict(report.visits_by_source),
            "visits_by_platform": dict(report.visits_by_platform),
            "visits_by_system": dict(report.visits_by_system),
            "sign_ups": report.sign_ups,
            "confirmed": report.confirmed,
            "with_a_receipt": report.with_a_receipt,
            "uploads": report.uploads,
            "receipts_read": report.receipts_read,
            "active_this_week": report.active_week,
            "active_this_month": report.active_month,
            "returning": report.returning,
        }
        return Answer(json.dumps(figures))


class ReplyReports(Reader):
    """The assistant replies users reported, newest first (F22.4.2)."""

    name = "admin_reply_reports"
    description = (
        "Admin only: assistant replies users reported as offensive, wrong or other — when, "
        "why, the reply's words and who reported it — newest first."
    )
    args = NoArgs
    needs = "admin"

    async def read(self, ctx: ToolContext, args: NoArgs) -> Answer:
        rows = await _service(ctx).reply_reports(LISTED)
        reports = [
            {
                "on": report.created_at.date().isoformat(),
                "reason": report.reason,
                "reply": report.reply_text[:300],
                "reported_by": email,
            }
            for report, email in rows
        ]
        return Answer(json.dumps({"reports": reports}))


class AdminLog(Reader):
    """What admins did to accounts lately, as the super admins' log shows it (F18.6.3)."""

    name = "admin_log"
    description = (
        "Super admin only: the latest admin actions — who did what to which account, when "
        "and why — newest first."
    )
    args = NoArgs
    needs = "super_admin"

    async def read(self, ctx: ToolContext, args: NoArgs) -> Answer:
        entries = [
            {
                "on": entry.action.created_at.isoformat(timespec="minutes"),
                "admin": entry.admin,
                "action": entry.action.action,
                "account": entry.target,
                "details": entry.action.details,
            }
            for entry in await _service(ctx).log(LISTED, 0)
        ]
        return Answer(json.dumps({"log": entries}, default=str))
