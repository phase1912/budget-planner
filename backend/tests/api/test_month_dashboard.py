"""The landing view's month in one response (F6.7, BRD D1, D4, D7, N2)."""

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import jwt
import pytest
from httpx import ASGITransport, AsyncClient
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


async def _dashboard(
    session: AsyncSession, user: User, year: int, month: int, today: str
) -> dict[str, Any]:
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
        response = await client.get(
            f"/api/v1/budget/months/{year}/{month}/dashboard", params={"today": today}
        )
    assert response.status_code == 200, response.json()
    body: dict[str, Any] = response.json()
    return body


def _merchants(body: dict[str, Any]) -> list[str]:
    return [r["merchant_name"] for r in body["receipts"]]


async def _named(
    session: AsyncSession, user: User, name: str, bought: datetime, amount: str
) -> None:
    receipt = await _receipt(session, user, bought, [amount], printed_total=amount)
    receipt.merchant_name = name
    await session.flush()


@pytest.mark.asyncio
async def test_a_running_month_comes_with_where_it_went_and_its_newest_receipts(
    db_session: AsyncSession,
) -> None:
    user = await UserFactory.create_async(budget_limit=Decimal("100.00"))
    await _named(db_session, user, "Early big", datetime(2026, 9, 2, tzinfo=UTC), "50.00")
    await _named(db_session, user, "Late small", datetime(2026, 9, 20, tzinfo=UTC), "5.00")

    body = await _dashboard(db_session, user, 2026, 9, today="2026-09-26")

    assert (body["summary"]["total"], body["summary"]["limit_percent"]) == ("55.00", 55)
    assert [(c["name"], c["total_amount"]) for c in body["categories"]] == [(None, "55.00")]
    assert _merchants(body) == ["Late small", "Early big"]
    assert body["receipts_in_month"] == 2


@pytest.mark.asyncio
async def test_a_finished_month_lists_its_biggest_receipts(db_session: AsyncSession) -> None:
    user = await UserFactory.create_async()
    await _named(db_session, user, "Early big", datetime(2026, 8, 2, tzinfo=UTC), "50.00")
    await _named(db_session, user, "Late small", datetime(2026, 8, 20, tzinfo=UTC), "5.00")

    body = await _dashboard(db_session, user, 2026, 8, today="2026-09-26")

    assert body["summary"]["is_complete"] is True
    assert _merchants(body) == ["Early big", "Late small"]


@pytest.mark.asyncio
async def test_the_receipts_and_categories_cover_exactly_the_month_the_figure_does(
    db_session: AsyncSession,
) -> None:
    """The last minute of August is August's; midnight on 1 September is not (D1, D2)."""
    user = await UserFactory.create_async()
    await _named(db_session, user, "Last minute", datetime(2026, 8, 31, 23, 59, tzinfo=UTC), "7.00")
    await _named(db_session, user, "Next month", datetime(2026, 9, 1, tzinfo=UTC), "9.00")
    held = await _receipt(
        db_session,
        user,
        None,  # type: ignore[arg-type]
        ["3.00"],
        status=ReceiptStatus.MANUAL_REVIEW,
        uploaded=datetime(2026, 8, 15, tzinfo=UTC),
    )
    held.merchant_name = "Undated"
    await db_session.flush()

    body = await _dashboard(db_session, user, 2026, 8, today="2026-09-26")

    assert body["summary"]["total"] == "7.00"
    assert sorted(_merchants(body)) == ["Last minute", "Undated"]
    assert [c["total_amount"] for c in body["categories"]] == ["7.00"]
    assert body["receipts_in_month"] == 2


@pytest.mark.asyncio
async def test_another_users_receipts_never_appear(db_session: AsyncSession) -> None:
    """BRD N2: the landing view is built from the caller's receipts alone."""
    owner = await UserFactory.create_async()
    stranger = await UserFactory.create_async()
    await _named(db_session, stranger, "Not yours", datetime(2026, 9, 3, tzinfo=UTC), "99.00")

    body = await _dashboard(db_session, owner, 2026, 9, today="2026-09-26")

    assert Decimal(body["summary"]["total"]) == 0
    assert (body["receipts"], body["categories"]) == ([], [])
    assert body["receipts_in_month"] == 0
