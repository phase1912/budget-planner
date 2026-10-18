"""Checking a goal before it is saved, against a real database (F23.13, N2)."""

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import jwt
import pytest
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.core.config import get_settings
from app.core.context import current_user_id
from app.db.session import get_db_session
from app.main import create_app
from app.models.user import User
from tests.api.test_budget_router import _receipt
from tests.factories.user import UserFactory


async def _check(session: AsyncSession, user: User, body: dict[str, Any]) -> Response:
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
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
        return await client.post("/api/v1/goals/check", json=body)


@pytest.mark.asyncio
async def test_a_ceiling_below_the_usual_months_is_a_stretch(db_session: AsyncSession) -> None:
    user = await UserFactory.create_async(usual_income=Decimal("3000.00"))
    for month in (7, 8, 9):
        await _receipt(db_session, user, datetime(2026, month, 10, tzinfo=UTC), ["1000.00"])

    response = await _check(
        db_session,
        user,
        {"financial_kind": "spending_ceiling", "target_amount": "800", "today": "2026-10-18"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["verdict"] == "stretch"
    assert body["usual"] == "1000"
    assert body["gap"] == "200"
    assert body["months"] == 3


@pytest.mark.asyncio
async def test_a_savings_target_within_what_is_left_is_doable(db_session: AsyncSession) -> None:
    user = await UserFactory.create_async(usual_income=Decimal("3000.00"))
    await _receipt(db_session, user, datetime(2026, 9, 10, tzinfo=UTC), ["1000.00"])

    body = (
        await _check(
            db_session,
            user,
            {"financial_kind": "savings_target", "target_amount": "1500", "today": "2026-10-18"},
        )
    ).json()

    assert body["verdict"] == "doable"
    assert body["usual"] == "2000"


@pytest.mark.asyncio
async def test_another_users_receipts_are_never_counted(db_session: AsyncSession) -> None:
    """N2: a newcomer is judged on their own empty history, not a stranger's months."""
    owner = await UserFactory.create_async()
    newcomer = await UserFactory.create_async()
    await _receipt(db_session, owner, datetime(2026, 9, 10, tzinfo=UTC), ["1000.00"])

    body = (
        await _check(
            db_session,
            newcomer,
            {"financial_kind": "spending_ceiling", "target_amount": "800", "today": "2026-10-18"},
        )
    ).json()

    assert body["verdict"] == "unknown"
    assert body["unknown"] == "no_history"


@pytest.mark.asyncio
async def test_a_target_of_zero_is_refused(db_session: AsyncSession) -> None:
    user = await UserFactory.create_async()

    response = await _check(
        db_session, user, {"financial_kind": "spending_ceiling", "target_amount": "0"}
    )

    assert response.status_code == 422
