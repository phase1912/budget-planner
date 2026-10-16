"""Deleting an account removes everything held about its owner (F17.9.1, BRD N2)."""

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routers import users as users_router
from app.core.security import create_access_token, get_password_hash
from app.db.session import get_db_session
from app.main import create_app
from app.models.base import Model
from app.models.household import Household, HouseholdMember, HouseholdRole
from app.models.line_item import LineItem
from app.models.refresh_token import RefreshToken
from app.models.user import User
from tests.factories.category import CategoryFactory
from tests.factories.goal import GoalFactory
from tests.factories.household import HouseholdFactory, HouseholdMemberFactory
from tests.factories.receipt import ReceiptFactory
from tests.factories.upload_job import UploadJobFactory
from tests.factories.user import UserFactory

PASSWORD = "Correct-Horse-42"


async def _delete(
    session: AsyncSession, user: User, password: str, monkeypatch: pytest.MonkeyPatch
) -> tuple[Response, list[str]]:
    removed: list[str] = []

    async def record(prefixes: list[str]) -> None:
        removed.extend(prefixes)

    async def same_session() -> AsyncIterator[AsyncSession]:
        yield session

    monkeypatch.setattr(users_router, "_remove_files", record)
    app = create_app()
    app.dependency_overrides[get_db_session] = same_session
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {create_access_token(user.id)}"},
    ) as client:
        response = await client.request("DELETE", "/users/me", json={"password": password})
    return response, removed


async def _owned_rows(session: AsyncSession, user_id: Any) -> dict[str, int]:
    """Rows in every table with a user_id column that still name this user."""
    counts = {}
    for table in Model.metadata.sorted_tables:
        if "user_id" in table.c:
            counts[table.name] = (
                await session.scalar(
                    select(func.count()).select_from(table).where(table.c.user_id == user_id)
                )
                or 0
            )
    return counts


async def _account_with_everything(session: AsyncSession) -> User:
    user = await UserFactory.create_async(password_hash=get_password_hash(PASSWORD))
    category = await CategoryFactory.create_async(user_id=user.id)
    receipt = await ReceiptFactory.create_async(user_id=user.id, file_ids=["photo-1"])
    session.add(
        LineItem(
            receipt_id=receipt.id,
            name="Milk",
            quantity=Decimal(1),
            unit_price=Decimal("3.00"),
            total_price=Decimal("3.00"),
            category_id=category.id,
        )
    )
    await GoalFactory.create_async(user_id=user.id)
    await UploadJobFactory.create_async(user_id=user.id)
    session.add(
        RefreshToken(
            user_id=user.id,
            token=f"t-{user.id}",
            family_id=user.id,
            expires_at=datetime.now(UTC) + timedelta(days=1),
        )
    )
    await session.flush()
    return user


@pytest.mark.asyncio
async def test_deleting_the_account_leaves_nothing_of_its_owner(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    user = await _account_with_everything(db_session)
    stranger = await _account_with_everything(db_session)
    user_id, before = user.id, await _owned_rows(db_session, user.id)
    assert sum(before.values()) >= 5

    response, removed = await _delete(db_session, user, PASSWORD, monkeypatch)

    assert response.status_code == 204
    left = await _owned_rows(db_session, user_id)
    assert {table: n for table, n in left.items() if n} == {}
    assert await db_session.get(User, user_id) is None
    assert removed == [f"receipts/{user_id}/", f"exports/{user_id}/"]
    assert sum((await _owned_rows(db_session, stranger.id)).values()) == sum(before.values())


@pytest.mark.asyncio
async def test_a_wrong_password_deletes_nothing(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    user = await _account_with_everything(db_session)

    response, removed = await _delete(db_session, user, "not-it", monkeypatch)

    assert (response.status_code, response.json()["code"]) == (403, "invalid_credentials")
    assert await db_session.get(User, user.id) is not None
    assert removed == []


@pytest.mark.asyncio
async def test_an_owner_leaving_hands_the_household_to_the_member_who_joined_first(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    owner = await UserFactory.create_async(password_hash=get_password_hash(PASSWORD))
    first, later = await UserFactory.create_async(), await UserFactory.create_async()
    household = await HouseholdFactory.create_async()
    await HouseholdMemberFactory.create_async(
        household_id=household.id, user_id=owner.id, role=HouseholdRole.OWNER.value
    )
    await HouseholdMemberFactory.create_async(
        household_id=household.id,
        user_id=first.id,
        created_at=datetime.now(UTC) - timedelta(days=2),
    )
    await HouseholdMemberFactory.create_async(
        household_id=household.id,
        user_id=later.id,
        created_at=datetime.now(UTC) - timedelta(days=1),
    )

    await _delete(db_session, owner, PASSWORD, monkeypatch)

    roles = {
        m.user_id: m.role
        for m in await db_session.scalars(
            select(HouseholdMember).where(HouseholdMember.household_id == household.id)
        )
    }
    assert roles == {first.id: HouseholdRole.OWNER, later.id: HouseholdRole.MEMBER}


@pytest.mark.asyncio
async def test_the_last_one_out_dissolves_the_household(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    owner = await UserFactory.create_async(password_hash=get_password_hash(PASSWORD))
    household = await HouseholdFactory.create_async()
    await HouseholdMemberFactory.create_async(
        household_id=household.id, user_id=owner.id, role=HouseholdRole.OWNER.value
    )
    household_id = household.id

    await _delete(db_session, owner, PASSWORD, monkeypatch)

    assert await db_session.get(Household, household_id) is None
