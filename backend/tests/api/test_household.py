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
