"""Spending day by day against a real database (F23.4, N2)."""

from collections.abc import AsyncGenerator
from datetime import UTC, datetime

import jwt
import pytest
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.core.config import get_settings
from app.core.context import current_user_id
from app.db.session import get_db_session
from app.main import create_app
from app.models.receipt import ReceiptStatus
from app.models.user import User
from tests.api.test_budget_router import _receipt
from tests.factories.user import UserFactory


async def _daily(session: AsyncSession, user: User, start: str, end: str, today: str) -> Response:
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
        return await client.get(
            "/api/v1/statistics/daily", params={"start": start, "end": end, "today": today}
        )


@pytest.mark.asyncio
async def test_each_day_carries_what_was_paid_on_it(db_session: AsyncSession) -> None:
    user = await UserFactory.create_async()
    await _receipt(db_session, user, datetime(2026, 10, 2, 9, tzinfo=UTC), ["10.00", "5.50"])
    await _receipt(db_session, user, datetime(2026, 10, 2, 23, 30, tzinfo=UTC), ["4.50"])
    await _receipt(db_session, user, datetime(2026, 10, 4, 12, tzinfo=UTC), ["20.00"])

    response = await _daily(db_session, user, "2026-10-01", "2026-10-05", "2026-10-05")

    assert response.status_code == 200
    body = response.json()
    assert [(d["day"], d["total"]) for d in body["days"]] == [
        ("2026-10-01", "0"),
        ("2026-10-02", "20.00"),
        ("2026-10-03", "0"),
        ("2026-10-04", "20.00"),
        ("2026-10-05", "0"),
    ]
    assert body["total"] == "40.00"
    assert body["average"] == "8.00"


@pytest.mark.asyncio
async def test_a_receipt_held_for_review_is_not_counted_on_its_day(
    db_session: AsyncSession,
) -> None:
    user = await UserFactory.create_async()
    await _receipt(
        db_session,
        user,
        datetime(2026, 10, 2, tzinfo=UTC),
        ["99.00"],
        status=ReceiptStatus.MANUAL_REVIEW,
    )

    body = (await _daily(db_session, user, "2026-10-02", "2026-10-02", "2026-10-02")).json()

    assert body["days"] == [{"day": "2026-10-02", "total": "0"}]


@pytest.mark.asyncio
async def test_another_users_spending_never_appears(db_session: AsyncSession) -> None:
    """N2: the days are the caller's own."""
    owner = await UserFactory.create_async()
    stranger = await UserFactory.create_async()
    await _receipt(db_session, owner, datetime(2026, 10, 2, tzinfo=UTC), ["50.00"])

    body = (await _daily(db_session, stranger, "2026-10-01", "2026-10-03", "2026-10-03")).json()

    assert body["total"] == "0"
