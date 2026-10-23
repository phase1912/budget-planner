"""The admin console by chat (F21.12): offered only to an admin signed in with a second
factor, checked again on saving, logged as from the console, and never reading another
user's receipts or money (N2)."""

import json
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.errors import DomainError
from app.assistant.api import session_access
from app.assistant.core.ports import ToolCall
from app.assistant.tools.base import Access
from app.assistant.tools.toolbox import Card, Toolbox, tool_specs
from app.core.config import get_settings
from app.core.context import current_user_id
from app.models.admin import AdminAction, PlanGrant
from app.models.user import User
from tests.factories.user import UserFactory

TODAY = datetime.now(UTC).date()


def _toolbox(session: AsyncSession, user: User, access: Access) -> Toolbox:
    current_user_id.set(user.id)
    return Toolbox(session, user, TODAY, access=access)


def test_admin_tools_are_offered_to_an_admin_session_only() -> None:
    names = {access: {s.name for s in tool_specs(access)} for access in ("user", "admin")}
    supers = {s.name for s in tool_specs("super_admin")}

    assert not any(n.startswith("admin_") for n in names["user"])
    assert {"admin_find_users", "admin_grant_plan"} <= names["admin"]
    assert "admin_set_admin" not in names["admin"] and "admin_set_admin" in supers


def test_an_admin_without_the_second_factor_is_a_user_to_the_assistant() -> None:
    admin = UserFactory.build(role="admin")
    settings = get_settings()

    without = session_access(admin, second_factor=False)

    assert without == ("user" if settings.requires_admin_second_factor else "admin")
    assert session_access(admin, second_factor=True) == "admin"


@pytest.mark.asyncio
async def test_an_admin_gives_the_paid_plan_by_chat_and_it_is_logged(
    db_session: AsyncSession,
) -> None:
    """The demo: "give anna@example.com the paid plan until December"."""
    admin = await UserFactory.create_async(role="admin")
    anna = await UserFactory.create_async(email="anna@example.com")
    toolbox = _toolbox(db_session, admin, "admin")
    until = TODAY + timedelta(days=40)

    card = await toolbox.propose(
        ToolCall(
            "admin_grant_plan",
            {"email": "anna@example.com", "until": until.isoformat(), "reason": "beta tester"},
        )
    )
    assert card is not None
    await toolbox.save(card)

    grant = (
        await db_session.execute(select(PlanGrant).where(PlanGrant.user_id == anna.id))
    ).scalar_one()
    logged = (
        await db_session.execute(select(AdminAction).where(AdminAction.target_user_id == anna.id))
    ).scalar_one()
    assert grant.ends_at.date() >= until and logged.admin_id == admin.id


@pytest.mark.asyncio
async def test_a_user_session_can_neither_read_nor_save_admin_tools(
    db_session: AsyncSession,
) -> None:
    user = await UserFactory.create_async()
    other = await UserFactory.create_async(email="other@example.com")
    toolbox = _toolbox(db_session, user, "user")

    read = json.loads(await toolbox.read(ToolCall("admin_account", {"email": "other@example.com"})))
    with pytest.raises(DomainError):
        await toolbox.save(
            Card("admin_confirm_email", {"target": other.email, "user_id": str(other.id)})
        )

    assert "error" in read


@pytest.mark.asyncio
async def test_an_accounts_facts_name_no_receipts_or_money(db_session: AsyncSession) -> None:
    admin = await UserFactory.create_async(role="admin")
    await UserFactory.create_async(email="anna@example.com")

    facts = json.loads(
        await _toolbox(db_session, admin, "admin").read(
            ToolCall("admin_account", {"email": "anna@example.com"})
        )
    )

    assert facts["email"] == "anna@example.com"
    assert not {"receipts", "balance", "incomes", "spent", "total"} & set(facts)
