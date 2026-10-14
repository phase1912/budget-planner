"""Trips, their receipts, and how a trip counts in the month (F20.1, N2)."""

import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, date, datetime
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
from app.domain.categories import ItemView
from app.domain.periods import DateRange
from app.main import create_app
from app.models.line_item import LineItem
from app.models.receipt import Receipt, ReceiptStatus
from app.models.user import User
from app.repository.household_spend import HouseholdSpendRepository
from app.repository.receipt import ReceiptRepository
from tests.factories.user import UserFactory

OCTOBER = DateRange(date(2026, 10, 1), date(2026, 10, 31))


async def _call(
    session: AsyncSession, user: User, method: str, path: str, **kwargs: Any
) -> Response:
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
        return await client.request(method, path, **kwargs)


async def _receipt(
    session: AsyncSession, user_id: uuid.UUID, day: int, amount: str, **fields: Any
) -> Receipt:
    receipt = Receipt(
        id=uuid.uuid4(),
        user_id=user_id,
        merchant_name="Shop",
        transaction_date=datetime(2026, 10, day, 12, tzinfo=UTC),
        total_amount=Decimal(amount),
        status=ReceiptStatus.PARSED,
        file_ids=[],
        line_items=[
            LineItem(
                id=uuid.uuid4(),
                name="Thing",
                quantity=Decimal(1),
                unit_price=Decimal(amount),
                total_price=Decimal(amount),
            )
        ],
        **fields,
    )
    session.add(receipt)
    await session.flush()
    return receipt


def _trip(kind: str, start: int, end: int, name: str = "Trip") -> dict[str, Any]:
    return {
        "kind": kind,
        "name": name,
        "country": "DE",
        "city": "Berlin",
        "start_date": f"2026-10-{start:02d}",
        "end_date": f"2026-10-{end:02d}",
    }


async def _dashboard(session: AsyncSession, user: User) -> dict[str, Any]:
    response = await _call(
        session,
        user,
        "GET",
        "/api/v1/budget/months/2026/10/dashboard",
        params={"today": "2026-10-31"},
    )
    return dict(response.json())


@pytest.mark.asyncio
async def test_receipts_dated_within_a_trip_join_it(db_session: AsyncSession) -> None:
    user = await UserFactory.create_async()
    await _receipt(db_session, user.id, 2, "10.00")
    await _receipt(db_session, user.id, 13, "30.00")
    await _receipt(db_session, user.id, 15, "20.00")

    created = await _call(db_session, user, "POST", "/api/v1/trips", json=_trip("business", 13, 15))
    detail = await _call(db_session, user, "GET", f"/api/v1/trips/{created.json()['id']}")

    assert created.status_code == 201
    assert (created.json()["receipt_count"], created.json()["total"]) == (2, "50.00")
    assert [r["total_amount"] for r in detail.json()["receipts"]] == ["30.00", "20.00"]


@pytest.mark.asyncio
async def test_a_business_trip_is_out_of_the_month_and_a_personal_one_in_it(
    db_session: AsyncSession,
) -> None:
    """The demo: Egypt stays in October, shown apart; Berlin is the employer's money."""
    user = await UserFactory.create_async()
    await _receipt(db_session, user.id, 3, "100.00")  # Egypt, personal
    await _receipt(db_session, user.id, 14, "60.00")  # Berlin, business
    await _receipt(db_session, user.id, 25, "40.00")  # at home
    await _call(db_session, user, "POST", "/api/v1/trips", json=_trip("personal", 1, 8, "Egypt"))
    await _call(db_session, user, "POST", "/api/v1/trips", json=_trip("business", 13, 15, "Berlin"))

    dashboard = await _dashboard(db_session, user)

    assert dashboard["summary"]["total"] == "140.00"
    assert {t["name"]: (t["kind"], t["total"]) for t in dashboard["trips"]} == {
        "Egypt": ("personal", "100.00"),
        "Berlin": ("business", "60.00"),
    }


@pytest.mark.asyncio
async def test_a_business_trip_is_out_of_statistics_advice_and_the_household(
    db_session: AsyncSession,
) -> None:
    """Each figure built on counted receipts leaves the employer's money out (F20.1.2)."""
    user = await UserFactory.create_async()
    await _receipt(db_session, user.id, 14, "60.00")
    await _receipt(db_session, user.id, 25, "40.00")
    await _call(db_session, user, "POST", "/api/v1/trips", json=_trip("business", 13, 15))
    current_user_id.set(user.id)
    receipts = ReceiptRepository(db_session)

    categories = await receipts.spend_by_category(ItemView.ALL, period=OCTOBER)
    spend = await receipts.item_spend(ItemView.ALL, period=OCTOBER)
    history, _ = await receipts.history_extent()
    members = await HouseholdSpendRepository(db_session).by_member(OCTOBER, [user.id])

    assert sum(c.total for c in categories) == Decimal("40.00")
    assert (spend.total, spend.excluded_count) == (Decimal("40.00"), 0)
    assert history == 1
    assert members[0].shared_total == Decimal("40.00")


@pytest.mark.asyncio
async def test_a_receipt_moved_by_hand_stays_where_it_was_put(db_session: AsyncSession) -> None:
    user = await UserFactory.create_async()
    inside = await _receipt(db_session, user.id, 14, "60.00")
    outside = await _receipt(db_session, user.id, 20, "15.00")
    trip = (
        await _call(db_session, user, "POST", "/api/v1/trips", json=_trip("business", 13, 15))
    ).json()
    inside_id, outside_id = inside.id, outside.id
    db_session.expunge_all()  # a real request starts with nothing loaded

    taken_out = await _call(
        db_session, user, "PUT", f"/api/v1/trips/receipts/{inside_id}", json={"trip_id": None}
    )
    put_in = await _call(
        db_session,
        user,
        "PUT",
        f"/api/v1/trips/receipts/{outside_id}",
        json={"trip_id": trip["id"]},
    )
    listed = (await _call(db_session, user, "GET", f"/api/v1/trips/{trip['id']}")).json()

    assert (taken_out.json()["trip"], taken_out.json()["trip_manual"]) == (None, True)
    assert put_in.json()["trip"]["name"] == "Trip"
    assert [r["id"] for r in listed["receipts"]] == [str(outside_id)]


@pytest.mark.asyncio
async def test_trips_cannot_share_a_day(db_session: AsyncSession) -> None:
    user = await UserFactory.create_async()
    await _call(db_session, user, "POST", "/api/v1/trips", json=_trip("personal", 1, 8, "Egypt"))

    clash = await _call(db_session, user, "POST", "/api/v1/trips", json=_trip("business", 8, 10))

    assert clash.status_code == 409
    assert clash.json()["code"] == "trips_overlap"
    assert clash.json()["params"] == {
        "name": "Egypt",
        "start_on": "2026-10-01",
        "end_on": "2026-10-08",
    }


@pytest.mark.asyncio
async def test_a_trip_ending_before_it_starts_is_refused(db_session: AsyncSession) -> None:
    user = await UserFactory.create_async()

    response = await _call(db_session, user, "POST", "/api/v1/trips", json=_trip("personal", 8, 1))

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_deleting_a_trip_gives_its_receipts_back_to_the_month(
    db_session: AsyncSession,
) -> None:
    user = await UserFactory.create_async()
    receipt = await _receipt(db_session, user.id, 14, "60.00")
    trip = (
        await _call(db_session, user, "POST", "/api/v1/trips", json=_trip("business", 13, 15))
    ).json()
    await _call(
        db_session,
        user,
        "PUT",
        f"/api/v1/trips/receipts/{receipt.id}",
        json={"trip_id": trip["id"]},
    )

    deleted = await _call(db_session, user, "DELETE", f"/api/v1/trips/{trip['id']}")

    assert deleted.status_code == 204
    assert (await _dashboard(db_session, user))["summary"]["total"] == "60.00"


@pytest.mark.asyncio
async def test_foreign_receipts_on_days_in_a_row_are_suggested_as_a_trip(
    db_session: AsyncSession,
) -> None:
    user = await UserFactory.create_async()
    for day in (3, 4):
        await _receipt(db_session, user.id, day, "20.00", original_currency="EUR")

    suggestions = (await _call(db_session, user, "GET", "/api/v1/trips/suggestions")).json()

    assert suggestions == [
        {
            "start": "2026-10-03",
            "end": "2026-10-04",
            "currency": "EUR",
            "receipts": 2,
            "amount": "40.00",
        }
    ]


@pytest.mark.asyncio
async def test_another_users_trip_and_receipts_are_out_of_reach(db_session: AsyncSession) -> None:
    """N2: their trip is not found, their receipt cannot be moved, and their dates are theirs."""
    owner, intruder = await UserFactory.create_async(), await UserFactory.create_async()
    receipt = await _receipt(db_session, owner.id, 14, "60.00")
    trip = (
        await _call(db_session, owner, "POST", "/api/v1/trips", json=_trip("business", 13, 15))
    ).json()
    mine = await _call(
        db_session, intruder, "POST", "/api/v1/trips", json=_trip("personal", 13, 15)
    )

    seen = await _call(db_session, intruder, "GET", f"/api/v1/trips/{trip['id']}")
    moved = await _call(
        db_session, intruder, "PUT", f"/api/v1/trips/receipts/{receipt.id}", json={"trip_id": None}
    )

    assert mine.status_code == 201  # another user's dates do not clash with one's own
    assert mine.json()["receipt_count"] == 0
    assert (seen.status_code, moved.status_code) == (404, 404)
