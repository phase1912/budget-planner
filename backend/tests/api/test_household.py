"""A household, its owner and its members (F12.2, ADR-0017, BRD N2)."""

from collections.abc import AsyncIterator
from typing import Any

import jwt
import pytest
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.core.config import get_settings
from app.core.context import current_user_id
from app.db.session import get_db_session
from app.main import create_app
from app.models.household import Household, HouseholdMember, HouseholdRole
from app.models.user import User
from tests.factories.household import HouseholdFactory, HouseholdMemberFactory
from tests.factories.user import UserFactory


async def _call(
    session: AsyncSession, user: User, method: str, url: str, json: Any = None
) -> Response:
    async def override_get_db() -> AsyncIterator[AsyncSession]:
        yield session

    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db_session] = override_get_db
    token = jwt.encode(
        {"sub": str(user.id)}, get_settings().jwt_secret_key.get_secret_value(), algorithm="HS256"
    )
    current_user_id.set(user.id)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {token}"},
    ) as client:
        return await client.request(method, url, json=json)


async def _household_of(owner: User, *members: User) -> Household:
    household = await HouseholdFactory.create_async()
    await HouseholdMemberFactory.create_async(
        household_id=household.id, user_id=owner.id, role=HouseholdRole.OWNER.value
    )
    for member in members:
        await HouseholdMemberFactory.create_async(household_id=household.id, user_id=member.id)
    return household


async def _households(session: AsyncSession) -> int:
    return await session.scalar(select(func.count()).select_from(Household)) or 0


URL = "/api/v1/household"


@pytest.mark.asyncio
async def test_a_user_without_a_household_has_none(db_session: AsyncSession) -> None:
    user = await UserFactory.create_async()

    response = await _call(db_session, user, "GET", URL)

    assert (response.status_code, response.json()) == (200, None)


@pytest.mark.asyncio
async def test_creating_a_household_makes_its_creator_the_owner(
    db_session: AsyncSession,
) -> None:
    user = await UserFactory.create_async(first_name="Bohdan")

    created = await _call(db_session, user, "POST", URL, {"name": "  Home  "})
    read = await _call(db_session, user, "GET", URL)

    assert created.status_code == 201, created.json()
    body = read.json()
    assert (body["name"], body["my_role"]) == ("Home", "owner")
    assert [(m["first_name"], m["role"]) for m in body["members"]] == [("Bohdan", "owner")]


@pytest.mark.asyncio
async def test_a_user_belongs_to_one_household_at_most(db_session: AsyncSession) -> None:
    owner, member = await UserFactory.create_async(), await UserFactory.create_async()
    await _household_of(owner, member)

    response = await _call(db_session, member, "POST", URL, {"name": "Second"})

    assert response.status_code == 409
    assert await _households(db_session) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("name", ["", "   ", "x" * 61])
async def test_a_household_needs_a_name_of_up_to_60_characters(
    db_session: AsyncSession, name: str
) -> None:
    user = await UserFactory.create_async()

    response = await _call(db_session, user, "POST", URL, {"name": name})

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_members_see_each_other(db_session: AsyncSession) -> None:
    owner = await UserFactory.create_async(first_name="Bohdan")
    member = await UserFactory.create_async(first_name="Anna")
    await _household_of(owner, member)

    body = (await _call(db_session, member, "GET", URL)).json()

    assert body["my_role"] == "member"
    assert {m["first_name"]: m["role"] for m in body["members"]} == {
        "Bohdan": "owner",
        "Anna": "member",
    }


@pytest.mark.asyncio
async def test_only_the_owner_renames_the_household(db_session: AsyncSession) -> None:
    owner, member = await UserFactory.create_async(), await UserFactory.create_async()
    await _household_of(owner, member)

    by_member = await _call(db_session, member, "PATCH", URL, {"name": "Mine now"})
    by_owner = await _call(db_session, owner, "PATCH", URL, {"name": "Family"})

    assert by_member.status_code == 403
    assert (by_owner.status_code, by_owner.json()["name"]) == (200, "Family")


@pytest.mark.asyncio
async def test_a_member_can_leave(db_session: AsyncSession) -> None:
    owner, member = await UserFactory.create_async(), await UserFactory.create_async()
    await _household_of(owner, member)

    response = await _call(db_session, member, "POST", f"{URL}/leave")

    assert response.status_code == 204
    assert (await _call(db_session, member, "GET", URL)).json() is None
    assert len((await _call(db_session, owner, "GET", URL)).json()["members"]) == 1


@pytest.mark.asyncio
async def test_the_owner_cannot_leave_others_behind(db_session: AsyncSession) -> None:
    owner, member = await UserFactory.create_async(), await UserFactory.create_async()
    await _household_of(owner, member)

    response = await _call(db_session, owner, "POST", f"{URL}/leave")

    assert response.status_code == 409
    assert (await _call(db_session, owner, "GET", URL)).json()["my_role"] == "owner"


@pytest.mark.asyncio
async def test_the_last_one_out_deletes_the_household(db_session: AsyncSession) -> None:
    owner = await UserFactory.create_async()
    await _household_of(owner)

    response = await _call(db_session, owner, "POST", f"{URL}/leave")

    assert response.status_code == 204
    assert await _households(db_session) == 0


@pytest.mark.asyncio
async def test_the_owner_removes_a_member(db_session: AsyncSession) -> None:
    owner, member = await UserFactory.create_async(), await UserFactory.create_async()
    await _household_of(owner, member)

    response = await _call(db_session, owner, "DELETE", f"{URL}/members/{member.id}")

    assert response.status_code == 200, response.json()
    assert [m["user_id"] for m in response.json()["members"]] == [str(owner.id)]
    assert (await _call(db_session, member, "GET", URL)).json() is None


@pytest.mark.asyncio
async def test_a_member_cannot_remove_anyone(db_session: AsyncSession) -> None:
    owner = await UserFactory.create_async()
    member, other = await UserFactory.create_async(), await UserFactory.create_async()
    await _household_of(owner, member, other)

    response = await _call(db_session, member, "DELETE", f"{URL}/members/{other.id}")

    assert response.status_code == 403
    count = await db_session.scalar(select(func.count()).select_from(HouseholdMember))
    assert count == 3


@pytest.mark.asyncio
async def test_the_owner_leaves_rather_than_removes_themselves(
    db_session: AsyncSession,
) -> None:
    owner = await UserFactory.create_async()
    await _household_of(owner)

    response = await _call(db_session, owner, "DELETE", f"{URL}/members/{owner.id}")

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_another_households_member_cannot_be_removed(db_session: AsyncSession) -> None:
    """N2: an owner reaches only their own household's members."""
    owner, stranger_owner = await UserFactory.create_async(), await UserFactory.create_async()
    stranger = await UserFactory.create_async()
    await _household_of(owner)
    await _household_of(stranger_owner, stranger)

    response = await _call(db_session, owner, "DELETE", f"{URL}/members/{stranger.id}")

    assert response.status_code == 404
    still = (await _call(db_session, stranger, "GET", URL)).json()
    assert still["my_role"] == "member"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method", "path", "json"),
    [("PATCH", "", {"name": "x"}), ("POST", "/leave", None)],
)
async def test_without_a_household_there_is_nothing_to_change(
    db_session: AsyncSession, method: str, path: str, json: Any
) -> None:
    user = await UserFactory.create_async()

    response = await _call(db_session, user, method, f"{URL}{path}", json)

    assert response.status_code == 404


# --- joining by invite link (F12.3) ------------------------------------------------


async def _invite_code(session: AsyncSession, owner: User) -> str:
    code = (await _call(session, owner, "GET", URL)).json()["invite_code"]
    assert isinstance(code, str) and len(code) == 32
    return code


@pytest.mark.asyncio
async def test_only_the_owner_is_given_the_invite_link(db_session: AsyncSession) -> None:
    owner, member = await UserFactory.create_async(), await UserFactory.create_async()
    await _household_of(owner, member)

    assert await _invite_code(db_session, owner)
    assert (await _call(db_session, member, "GET", URL)).json()["invite_code"] is None


@pytest.mark.asyncio
async def test_an_invite_link_says_whose_household_it_is(db_session: AsyncSession) -> None:
    owner = await UserFactory.create_async(first_name="Bohdan", last_name="R")
    await _household_of(owner)
    code = await _invite_code(db_session, owner)
    guest = await UserFactory.create_async()

    response = await _call(db_session, guest, "GET", f"{URL}/invites/{code}")

    assert response.json() == {"name": "Home", "owner_name": "Bohdan R", "member_count": 1}


@pytest.mark.asyncio
async def test_joining_by_invite_link_makes_a_member(db_session: AsyncSession) -> None:
    owner = await UserFactory.create_async(currency="PLN")
    guest = await UserFactory.create_async(currency="PLN", first_name="Anna")
    await _household_of(owner)
    code = await _invite_code(db_session, owner)

    response = await _call(db_session, guest, "POST", f"{URL}/join", {"code": code})

    assert response.status_code == 200, response.json()
    body = response.json()
    assert (body["my_role"], body["invite_code"]) == ("member", None)
    assert len((await _call(db_session, owner, "GET", URL)).json()["members"]) == 2


@pytest.mark.asyncio
async def test_someone_in_a_household_cannot_join_another(db_session: AsyncSession) -> None:
    owner, other_owner = await UserFactory.create_async(), await UserFactory.create_async()
    await _household_of(owner)
    await _household_of(other_owner)
    code = await _invite_code(db_session, owner)

    response = await _call(db_session, other_owner, "POST", f"{URL}/join", {"code": code})

    assert response.status_code == 409
    assert "already belong" in response.json()["detail"]


@pytest.mark.asyncio
async def test_an_account_in_another_currency_cannot_join(db_session: AsyncSession) -> None:
    """The household's totals are in one currency (ADR-0017)."""
    owner = await UserFactory.create_async(currency="PLN")
    guest = await UserFactory.create_async(currency="USD")
    await _household_of(owner)
    code = await _invite_code(db_session, owner)

    response = await _call(db_session, guest, "POST", f"{URL}/join", {"code": code})

    assert response.status_code == 409
    assert "PLN" in response.json()["detail"] and "USD" in response.json()["detail"]
    assert (await _call(db_session, guest, "GET", URL)).json() is None


@pytest.mark.asyncio
async def test_a_regenerated_link_stops_the_old_one_working(db_session: AsyncSession) -> None:
    owner = await UserFactory.create_async(currency="PLN")
    guest = await UserFactory.create_async(currency="PLN")
    await _household_of(owner)
    old = await _invite_code(db_session, owner)

    regenerated = await _call(db_session, owner, "POST", f"{URL}/invite/regenerate")
    joined = await _call(db_session, guest, "POST", f"{URL}/join", {"code": old})
    preview = await _call(db_session, guest, "GET", f"{URL}/invites/{old}")

    assert regenerated.json()["invite_code"] not in (None, old)
    assert (joined.status_code, preview.status_code) == (404, 404)


@pytest.mark.asyncio
async def test_only_the_owner_regenerates_the_link(db_session: AsyncSession) -> None:
    owner, member = await UserFactory.create_async(), await UserFactory.create_async()
    await _household_of(owner, member)

    response = await _call(db_session, member, "POST", f"{URL}/invite/regenerate")

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_a_made_up_code_leads_nowhere(db_session: AsyncSession) -> None:
    guest = await UserFactory.create_async()

    response = await _call(db_session, guest, "POST", f"{URL}/join", {"code": "0" * 32})

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_probing_invite_links_is_rate_limited(db_session: AsyncSession) -> None:
    """F10.6: codes cannot be guessed, and a script cannot try many of them either."""
    guest = await UserFactory.create_async()

    answers = [
        (await _call(db_session, guest, "GET", f"{URL}/invites/{n:032d}")).status_code
        for n in range(11)
    ]

    assert answers[:10] == [404] * 10
    assert answers[10] == 429
