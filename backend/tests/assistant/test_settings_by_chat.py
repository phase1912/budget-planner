"""Settings and the family by chat (F21.11, ADR-0029): one card per setting, as it is and as
it will be, saved as from Settings; the family's roles and members as on its screen."""

import json
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.assistant.core.ports import ToolCall
from app.assistant.tools.toolbox import Toolbox
from app.core.context import current_user_id
from app.models.household import HouseholdMember, HouseholdRole
from app.models.user import User
from tests.api.test_household import _household_of
from tests.assistant.test_tools import _approve, _propose
from tests.factories.user import UserFactory

TODAY = datetime.now(UTC).date()


def _toolbox(session: AsyncSession, user: User) -> Toolbox:
    current_user_id.set(user.id)
    return Toolbox(session, user, TODAY)


@pytest.mark.asyncio
async def test_language_palette_and_payday_are_three_cards_saved_as_from_settings(
    db_session: AsyncSession,
) -> None:
    """The demo: "switch to Polish and the dark palette, payday is the 10th"."""
    me = await UserFactory.create_async(language="en", palette="daylight", payday=1)

    cards = await _propose(
        db_session,
        me,
        ToolCall("change_setting", {"setting": "language", "value": "pl"}),
        ToolCall("change_setting", {"setting": "palette", "value": "midnight"}),
        ToolCall("change_setting", {"setting": "payday", "value": "10"}),
    )
    assert [c["card"]["fields"]["target"] for c in cards] == [
        "language: en → pl",
        "palette: daylight → midnight",
        "payday: 1 → 10",
    ]
    for card in cards:
        await _approve(db_session, me, card)

    me_id = me.id
    db_session.expire_all()
    saved = (await db_session.execute(select(User).where(User.id == me_id))).scalar_one()
    assert (saved.language, saved.palette, saved.payday) == ("pl", "midnight", 10)


@pytest.mark.asyncio
async def test_a_setting_the_screen_would_refuse_is_no_card(db_session: AsyncSession) -> None:
    me = await UserFactory.create_async()
    toolbox = _toolbox(db_session, me)

    assert (
        await toolbox.check(ToolCall("change_setting", {"setting": "payday", "value": "40"}))
        is not None
    )
    assert (
        await toolbox.check(ToolCall("change_setting", {"setting": "language", "value": "de"}))
        is not None
    )
    assert (
        await toolbox.check(ToolCall("change_setting", {"setting": "tax_rate", "value": "12,5"}))
        is None
    )


@pytest.mark.asyncio
async def test_what_is_set_is_read_back(db_session: AsyncSession) -> None:
    me = await UserFactory.create_async(payday=25, usual_income=Decimal("6000"))

    figures = json.loads(await _toolbox(db_session, me).read(ToolCall("settings", {})))

    assert (figures["payday"], figures["usual_income"]) == ("25", "6000.00")


@pytest.mark.asyncio
async def test_the_owner_marks_a_member_a_child_and_takes_another_out(
    db_session: AsyncSession,
) -> None:
    me = await UserFactory.create_async(first_name="Bohdan")
    kid = await UserFactory.create_async(first_name="Mia")
    guest = await UserFactory.create_async(first_name="Olek")
    await _household_of(me, kid, guest)

    family = json.loads(await _toolbox(db_session, me).read(ToolCall("family", {})))
    [role] = await _propose(
        db_session, me, ToolCall("family_role", {"member": "mia", "role": "child"})
    )
    await _approve(db_session, me, role)
    [removal] = await _propose(db_session, me, ToolCall("family_remove", {"member": "Olek"}))
    await _approve(db_session, me, removal)

    assert {m["name"] for m in family["members"]} == {"Bohdan", "Mia", "Olek"}
    kid_id, guest_id = kid.id, guest.id
    db_session.expire_all()
    members = {
        m.user_id: m.role
        for m in (await db_session.execute(select(HouseholdMember))).scalars()
        if m.user_id in (kid_id, guest_id)
    }
    assert members == {kid_id: HouseholdRole.CHILD}


@pytest.mark.asyncio
async def test_no_one_outside_the_family_is_found_by_name(db_session: AsyncSession) -> None:
    me = await UserFactory.create_async(first_name="Bohdan")
    await _household_of(me)
    await UserFactory.create_async(first_name="Stranger")

    refused = await _toolbox(db_session, me).check(
        ToolCall("family_remove", {"member": "Stranger"})
    )

    assert refused is not None


def test_signing_in_and_deleting_the_account_have_no_tool() -> None:
    """ADR-0029: the password, the address, the second factor and deleting the account stay
    on their screens — no tool a user is offered is named for them or takes them. An admin's
    tools name accounts by address and send reset links, but never set either (F21.12)."""
    from app.assistant.tools import all_tools

    guarded = ("password", "email", "two_factor", "totp", "delete_account")
    for tool in (t for t in all_tools().values() if t.needs == "user"):
        spec = json.dumps(tool.spec().parameters).lower() + tool.spec().name
        assert not any(word in spec for word in guarded), tool.spec().name
