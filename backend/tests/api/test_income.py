"""Money coming in, and the account's appearance and setup (F23.10, F23.1, F23.9, N2)."""

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.db.session import get_db_session
from app.main import create_app
from app.models.receipt import ReceiptStatus
from app.models.user import User
from tests.factories.line_item import LineItemFactory
from tests.factories.receipt import ReceiptFactory
from tests.factories.user import UserFactory


async def _call(
    session: AsyncSession, method: str, url: str, *, user: User, json: Any = None
) -> Response:
    async def same_session() -> AsyncIterator[AsyncSession]:
        yield session

    app = create_app()
    app.dependency_overrides[get_db_session] = same_session
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {create_access_token(user.id)}"},
    ) as client:
        return await client.request(method, url, json=json)


@pytest.mark.asyncio
async def test_the_usual_income_stands_in_until_the_month_has_entries(
    db_session: AsyncSession,
) -> None:
    user = await UserFactory.create_async()
    await _call(db_session, "PATCH", "/users/me", user=user, json={"usual_income": "6800.00"})

    empty = (await _call(db_session, "GET", "/api/v1/income?month=2026-10", user=user)).json()
    assert empty["total"] == "6800.00" and empty["entered"] is False

    added = await _call(
        db_session,
        "POST",
        "/api/v1/income",
        user=user,
        json={"received_on": "2026-10-10", "amount": "6200.00", "source": "ACME"},
    )
    assert added.status_code == 201
    await _call(
        db_session,
        "POST",
        "/api/v1/income",
        user=user,
        json={"received_on": "2026-11-01", "amount": "100.00", "source": "Next month"},
    )
    october = (await _call(db_session, "GET", "/api/v1/income?month=2026-10", user=user)).json()
    assert october["total"] == "6200.00" and october["entered"] is True
    assert [e["source"] for e in october["entries"]] == ["ACME"]


@pytest.mark.asyncio
async def test_another_users_income_cannot_be_changed_or_seen(db_session: AsyncSession) -> None:
    ann = await UserFactory.create_async()
    bob = await UserFactory.create_async()
    entry = (
        await _call(
            db_session,
            "POST",
            "/api/v1/income",
            user=ann,
            json={"received_on": "2026-10-10", "amount": "10.00", "source": "Gift"},
        )
    ).json()

    body = {"received_on": "2026-10-10", "amount": "99.00", "source": "Mine now"}
    url = f"/api/v1/income/{entry['id']}"
    assert (await _call(db_session, "PUT", url, user=bob, json=body)).status_code == 404
    assert (await _call(db_session, "DELETE", url, user=bob)).status_code == 404
    bobs = (await _call(db_session, "GET", "/api/v1/income?month=2026-10", user=bob)).json()
    assert bobs["entries"] == []


@pytest.mark.asyncio
async def test_the_look_and_the_first_sign_in_are_kept_on_the_account(
    db_session: AsyncSession,
) -> None:
    user = await UserFactory.create_async()
    me = (await _call(db_session, "GET", "/users/me", user=user)).json()
    assert me["palette"] is None and me["onboarded_at"] is None

    changed = await _call(
        db_session,
        "PATCH",
        "/users/me",
        user=user,
        json={
            "palette": "rose",
            "dark_at_night": True,
            "travels_for_work": True,
            "onboarded": True,
        },
    )
    body = changed.json()
    assert body["palette"] == "rose" and body["dark_at_night"] and body["travels_for_work"]
    assert body["onboarded_at"] is not None

    refused = await _call(db_session, "PATCH", "/users/me", user=user, json={"palette": "neon"})
    assert refused.status_code == 422


@pytest.mark.asyncio
async def test_the_balance_moves_with_income_and_counted_purchases_since_it_was_entered(
    db_session: AsyncSession,
) -> None:
    user = await UserFactory.create_async()
    url = "/api/v1/income/balance?today=2026-10-20"
    assert (await _call(db_session, "GET", url, user=user)).json()["balance"] is None

    await _call(
        db_session,
        "PATCH",
        "/users/me",
        user=user,
        json={"starting_balance": "5000.00", "balance_since": "2026-10-01"},
    )
    for day, amount, status in [
        (5, "169.00", ReceiptStatus.PARSED),
        (6, "40.00", ReceiptStatus.MANUAL_REVIEW),  # not counted until resolved (D3)
    ]:
        receipt = await ReceiptFactory.create_async(
            user_id=user.id,
            transaction_date=datetime(2026, 10, day, tzinfo=UTC),
            total_amount=Decimal(amount),
            status=status,
            file_ids=[],
        )
        await LineItemFactory.create_async(
            receipt=receipt,
            name="Thing",
            quantity=Decimal(1),
            unit_price=Decimal(amount),
            total_price=Decimal(amount),
            category=None,
        )
    await ReceiptFactory.create_async(  # before the start: not in the balance
        user_id=user.id,
        transaction_date=datetime(2026, 9, 30, tzinfo=UTC),
        status=ReceiptStatus.PARSED,
        file_ids=[],
    )
    after_purchase = (await _call(db_session, "GET", url, user=user)).json()
    assert after_purchase["balance"] == "4831.00"

    await _call(
        db_session,
        "POST",
        "/api/v1/income",
        user=user,
        json={"received_on": "2026-10-10", "amount": "6200.00", "source": "ACME"},
    )
    after_salary = (await _call(db_session, "GET", url, user=user)).json()
    assert after_salary == {
        "balance": "11031.00",
        "since": "2026-10-01",
        "starting": "5000.00",
        "came_in": "6200.00",
        "spent": "169.00",
    }
