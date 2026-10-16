"""Trips, their receipts, how a trip counts in the month, and what it cost (F20.1-2, N2)."""

import io
import re
import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any, cast
from unittest.mock import AsyncMock, patch

import jwt
import pytest
from httpx import ASGITransport, AsyncClient, Response
from PIL import Image
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_exchange_rates
from app.core.config import get_settings
from app.core.context import current_user_id
from app.db.session import get_db_session
from app.domain.categories import ItemView
from app.domain.currency import ExchangeRate
from app.domain.periods import DateRange
from app.domain.trips import ExpenseKind
from app.main import create_app
from app.models.category import Category
from app.models.export_job import ExportFormat, ExportJob, ExportKind
from app.models.line_item import LineItem
from app.models.receipt import Receipt, ReceiptStatus
from app.models.user import User
from app.ports.exchange_rates import ExchangeRatePort
from app.ports.storage import StoragePort
from app.repository.household_spend import HouseholdSpendRepository
from app.repository.receipt import ReceiptRepository
from app.services.export import ExportService
from tests.api.test_upload_wizard_persistence import _job
from tests.factories.category import CategoryFactory
from tests.factories.user import UserFactory

OCTOBER = DateRange(date(2026, 10, 1), date(2026, 10, 31))


async def _call(
    session: AsyncSession,
    user: User,
    method: str,
    path: str,
    rates: ExchangeRatePort | None = None,
    **kwargs: Any,
) -> Response:
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield session

    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db_session] = override_get_db
    if rates is not None:
        app.dependency_overrides[get_exchange_rates] = lambda: rates
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
        status=fields.pop("status", ReceiptStatus.PARSED),
        file_ids=fields.pop("file_ids", []),
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


async def _answer(
    session: AsyncSession, user: User, receipt_id: uuid.UUID, trip_id: str | None
) -> Response:
    """The user says a receipt is the trip's (`trip_id`) or not on any trip (None)."""
    return await _call(
        session, user, "PUT", f"/api/v1/trips/receipts/{receipt_id}", json={"trip_id": trip_id}
    )


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
async def test_receipts_dated_within_a_personal_trip_join_it(db_session: AsyncSession) -> None:
    user = await UserFactory.create_async()
    await _receipt(db_session, user.id, 2, "10.00")
    await _receipt(db_session, user.id, 13, "30.00")
    await _receipt(db_session, user.id, 15, "20.00")

    created = await _call(db_session, user, "POST", "/api/v1/trips", json=_trip("personal", 13, 15))
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
    berlin = await _receipt(db_session, user.id, 14, "60.00")  # Berlin, business
    await _receipt(db_session, user.id, 25, "40.00")  # at home
    await _call(db_session, user, "POST", "/api/v1/trips", json=_trip("personal", 1, 8, "Egypt"))
    trip = await _call(
        db_session, user, "POST", "/api/v1/trips", json=_trip("business", 13, 15, "Berlin")
    )
    await _answer(db_session, user, berlin.id, trip.json()["id"])

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
    berlin = await _receipt(db_session, user.id, 14, "60.00")
    await _receipt(db_session, user.id, 25, "40.00")
    trip = await _call(db_session, user, "POST", "/api/v1/trips", json=_trip("business", 13, 15))
    await _answer(db_session, user, berlin.id, trip.json()["id"])
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


async def _builtin(session: AsyncSession, name: str) -> Category:
    category = await session.scalar(
        select(Category).where(Category.name == name, Category.user_id.is_(None))
    )
    assert category is not None
    return category


@pytest.mark.asyncio
async def test_a_trip_splits_into_kinds_in_the_account_currency_and_per_currency_paid(
    db_session: AsyncSession,
) -> None:
    """F20.2 demo: the guess, the categories of an older receipt, and what was paid in EGP."""
    user = await UserFactory.create_async(currency="PLN")
    await _receipt(db_session, user.id, 2, "1900.00", expense_kind=ExpenseKind.TRANSPORT)
    dinner = await _receipt(db_session, user.id, 3, "310.00")  # read before kinds were
    dinner.line_items[0].category_id = (await _builtin(db_session, "Dining")).id
    await _receipt(
        db_session,
        user.id,
        4,
        "630.00",
        expense_kind=ExpenseKind.OTHER,
        original_currency="EGP",
        original_total=Decimal("7600.00"),
        exchange_rate=Decimal("0.0829"),
    )
    trip = (
        await _call(db_session, user, "POST", "/api/v1/trips", json=_trip("personal", 1, 8))
    ).json()
    db_session.expunge_all()

    detail = (await _call(db_session, user, "GET", f"/api/v1/trips/{trip['id']}")).json()

    assert [(k["kind"], k["total"]) for k in detail["by_kind"]] == [
        ("transport", "1900.00"),
        ("accommodation", "0.00"),
        ("meals", "310.00"),
        ("other", "630.00"),
    ]
    assert [(c["currency"], c["total"]) for c in detail["by_currency"]] == [
        ("EGP", "7600.00"),
        ("PLN", "2210.00"),
    ]
    assert [(r["expense_kind"], r["expense_kind_chosen"]) for r in detail["receipts"]] == [
        ("transport", False),
        ("meals", False),
        ("other", False),
    ]


@pytest.mark.asyncio
async def test_the_users_kind_wins_over_the_guess_until_given_back(
    db_session: AsyncSession,
) -> None:
    """F20.2: a taxi filed as other moves to transport, and the totals follow."""
    user = await UserFactory.create_async()
    taxi = await _receipt(db_session, user.id, 14, "45.00", expense_kind=ExpenseKind.OTHER)
    trip = (
        await _call(db_session, user, "POST", "/api/v1/trips", json=_trip("personal", 13, 15))
    ).json()
    taxi_id = taxi.id
    db_session.expunge_all()

    chosen = await _call(
        db_session,
        user,
        "PUT",
        f"/api/v1/trips/receipts/{taxi_id}/kind",
        json={"kind": "transport"},
    )
    after = (await _call(db_session, user, "GET", f"/api/v1/trips/{trip['id']}")).json()
    given_back = await _call(
        db_session, user, "PUT", f"/api/v1/trips/receipts/{taxi_id}/kind", json={"kind": None}
    )

    assert (chosen.json()["expense_kind"], chosen.json()["expense_kind_chosen"]) == (
        "transport",
        True,
    )
    totals = {k["kind"]: k["total"] for k in after["by_kind"]}
    assert (totals["transport"], totals["other"]) == ("45.00", "0.00")
    assert (given_back.json()["expense_kind"], given_back.json()["expense_kind_chosen"]) == (
        "other",
        False,
    )


@pytest.mark.asyncio
async def test_a_kind_the_model_names_is_kept_with_the_receipt_and_nonsense_is_not(
    db_session: AsyncSession,
) -> None:
    """F20.2: the guess is made by the same reading that finds the shop and the lines."""
    user = await UserFactory.create_async()
    current_user_id.set(user.id)
    repository = ReceiptRepository(db_session)

    hotel = repository.create_from_extraction(
        user.id, [], {"merchant_name": "Hotel Adlon", "expense_kind": "accommodation"}, "test"
    )
    odd = repository.create_from_extraction(
        user.id, [], {"merchant_name": "Kiosk", "expense_kind": "snacks"}, "test"
    )

    assert (hotel.expense_kind, odd.expense_kind) == (ExpenseKind.ACCOMMODATION, None)


@pytest.mark.asyncio
async def test_another_users_receipt_kind_cannot_be_changed(db_session: AsyncSession) -> None:
    """N2."""
    owner, intruder = await UserFactory.create_async(), await UserFactory.create_async()
    receipt = await _receipt(db_session, owner.id, 14, "60.00")

    changed = await _call(
        db_session,
        intruder,
        "PUT",
        f"/api/v1/trips/receipts/{receipt.id}/kind",
        json={"kind": "meals"},
    )

    assert changed.status_code == 404
    assert receipt.expense_kind_chosen is None


@pytest.mark.asyncio
async def test_a_business_trip_asks_about_its_days_receipts_and_counts_none_unanswered(
    db_session: AsyncSession,
) -> None:
    """A purchase on a business trip may be the user's own: it stays theirs until answered."""
    user = await UserFactory.create_async()
    taxi = await _receipt(db_session, user.id, 13, "45.00")
    phone = await _receipt(db_session, user.id, 14, "3999.00")
    trip = (
        await _call(db_session, user, "POST", "/api/v1/trips", json=_trip("business", 13, 15))
    ).json()
    taxi_id, phone_id = taxi.id, phone.id

    before = (await _call(db_session, user, "GET", f"/api/v1/trips/{trip['id']}")).json()
    listed = (await _call(db_session, user, "GET", "/receipts")).json()["items"]
    month_before = (await _dashboard(db_session, user))["summary"]["total"]

    await _answer(db_session, user, taxi_id, trip["id"])
    await _answer(db_session, user, phone_id, None)
    after = (await _call(db_session, user, "GET", f"/api/v1/trips/{trip['id']}")).json()
    month_after = (await _dashboard(db_session, user))["summary"]["total"]

    assert (before["receipt_count"], before["asking_count"]) == (0, 2)
    assert {r["id"] for r in before["asking"]} == {str(taxi_id), str(phone_id)}
    assert {r["trip_question"]["name"] for r in listed} == {"Trip"}
    assert month_before == "4044.00"
    assert (after["receipt_count"], after["total"], after["asking_count"]) == (1, "45.00", 0)
    assert month_after == "3999.00"


@pytest.mark.asyncio
async def test_the_receipts_list_names_the_trip_each_receipt_is_on(
    db_session: AsyncSession,
) -> None:
    user = await UserFactory.create_async()
    await _receipt(db_session, user.id, 3, "100.00")
    await _receipt(db_session, user.id, 25, "40.00")
    await _call(db_session, user, "POST", "/api/v1/trips", json=_trip("personal", 1, 8, "Egypt"))

    listed = (await _call(db_session, user, "GET", "/receipts")).json()["items"]

    assert [(r["total_amount"], r["trip"] and r["trip"]["name"]) for r in listed] == [
        ("40.00", None),
        ("100.00", "Egypt"),
    ]


@pytest.mark.asyncio
async def test_a_receipt_stored_from_the_wizard_goes_where_the_user_answered(
    db_session: AsyncSession,
) -> None:
    """Asked in the wizard, or uploaded from the trip's page: the answer is kept by hand."""
    user = await UserFactory.create_async(currency="PLN")
    trip = (
        await _call(db_session, user, "POST", "/api/v1/trips", json=_trip("business", 13, 15))
    ).json()
    reading = {
        "merchant_name": "Taxi Berlin",
        "currency": "PLN",
        "transaction_date": "2026-10-14",
        "receipt_total": "45.00",
        "items_sum_matches_total": True,
        "line_items": [
            {"name": "Ride", "quantity": "1", "unit_price": "45.00", "total_price": "45.00"}
        ],
    }
    yes, no = await _job(user, reading), await _job(user, reading)

    stored_yes = await _call(
        db_session,
        user,
        "POST",
        f"/receipts/upload/{yes.id}/commit",
        json={"indices_to_store": [0], "trips": [{"index": 0, "trip_id": trip["id"]}]},
    )
    stored_no = await _call(
        db_session,
        user,
        "POST",
        f"/receipts/upload/{no.id}/commit",
        json={"indices_to_store": [0], "trips": [{"index": 0, "trip_id": None}]},
    )
    detail = (await _call(db_session, user, "GET", f"/api/v1/trips/{trip['id']}")).json()

    assert (stored_yes.status_code, stored_no.status_code) == (200, 200)
    assert (detail["receipt_count"], detail["asking_count"]) == (1, 0)


@pytest.mark.asyncio
async def test_a_receipt_cannot_be_stored_into_another_users_trip(
    db_session: AsyncSession,
) -> None:
    """N2: the wizard's answer names a trip the caller does not own."""
    owner, intruder = await UserFactory.create_async(), await UserFactory.create_async()
    trip = (
        await _call(db_session, owner, "POST", "/api/v1/trips", json=_trip("business", 13, 15))
    ).json()
    job = await _job(
        intruder,
        {
            "merchant_name": "Shop",
            "transaction_date": "2026-10-14",
            "receipt_total": "5.00",
            "items_sum_matches_total": True,
            "line_items": [
                {"name": "Pen", "quantity": "1", "unit_price": "5.00", "total_price": "5.00"}
            ],
        },
    )

    stored = await _call(
        db_session,
        intruder,
        "POST",
        f"/receipts/upload/{job.id}/commit",
        json={"indices_to_store": [0], "trips": [{"index": 0, "trip_id": trip["id"]}]},
    )

    assert stored.status_code == 404


@pytest.mark.asyncio
async def test_a_personal_trip_has_a_budget_its_days_and_its_categories(
    db_session: AsyncSession,
) -> None:
    """F20.3 demo: 3 000 for the mountains, day by day, 380 left."""
    user = await UserFactory.create_async(currency="PLN")
    await _receipt(db_session, user.id, 10, "1120.00")
    await _receipt(db_session, user.id, 11, "860.00")
    await _receipt(db_session, user.id, 12, "640.00")
    dining = (await _builtin(db_session, "Dining")).id
    created = await _call(
        db_session,
        user,
        "POST",
        "/api/v1/trips",
        json={**_trip("personal", 10, 12, "Mountains"), "budget": "3000.00"},
    )
    trip_id = created.json()["id"]
    db_session.expunge_all()
    await db_session.execute(
        update(LineItem)
        .where(LineItem.receipt_id.in_(select(Receipt.id).where(Receipt.user_id == user.id)))
        .values(category_id=dining)
    )

    detail = (await _call(db_session, user, "GET", f"/api/v1/trips/{trip_id}")).json()

    assert (created.json()["budget"], created.json()["budget_left"]) == ("3000.00", "380.00")
    assert [(d["day"], d["total"]) for d in detail["days"]] == [
        ("2026-10-10", "1120.00"),
        ("2026-10-11", "860.00"),
        ("2026-10-12", "640.00"),
    ]
    assert detail["categories"] == [{"category": "Dining", "total": "2620.00"}]


@pytest.mark.asyncio
async def test_a_business_trip_takes_no_budget(db_session: AsyncSession) -> None:
    """F20.3: the employer's money is not the user's to budget."""
    user = await UserFactory.create_async()

    refused = await _call(
        db_session,
        user,
        "POST",
        "/api/v1/trips",
        json={**_trip("business", 13, 15), "budget": "500.00"},
    )

    assert refused.status_code == 422


class _EuroAt425:
    """The NBP mid rate of the euro, as a stub: 4.25 zł, published the day asked for."""

    async def rate(self, base: str, quote: str, on: date) -> ExchangeRate:
        return ExchangeRate(base, quote, Decimal("4.25"), on, "NBP")


def _times(**overrides: Any) -> dict[str, Any]:
    return {
        "departure": "2026-10-13T06:00:00+02:00",
        "returned": "2026-10-15T21:00:00+02:00",
        "meals": [["breakfast"], ["breakfast"], []],
        **overrides,
    }


@pytest.mark.asyncio
async def test_a_business_trips_per_diem_is_itemised_and_put_into_zloty(
    db_session: AsyncSession,
) -> None:
    """F20.4 demo: Germany, 13 Oct 06:00 to 15 Oct 21:00, two hotel breakfasts."""
    user = await UserFactory.create_async(currency="PLN")
    trip = (
        await _call(db_session, user, "POST", "/api/v1/trips", json=_trip("business", 13, 15))
    ).json()

    given = await _call(
        db_session,
        user,
        "PUT",
        f"/api/v1/trips/{trip['id']}/per-diem",
        rates=_EuroAt425(),
        json=_times(),
    )
    detail = (
        await _call(db_session, user, "GET", f"/api/v1/trips/{trip['id']}", rates=_EuroAt425())
    ).json()

    assert given.status_code == 200, given.json()
    [abroad] = given.json()["parts"]
    assert (abroad["currency"], abroad["rate"], abroad["total"]) == ("EUR", "49", "132.30")
    assert [(d["rule"], d["reduction"]) for d in abroad["days"]] == [
        ("§ 13 ust. 3 pkt 1", "7.35"),
        ("§ 13 ust. 3 pkt 1", "7.35"),
        ("§ 13 ust. 3 pkt 2 lit. c", "0.00"),
    ]
    assert given.json()["total_pln"] == "562.28"
    assert given.json()["to_pln"][0]["effective_date"] == "2026-10-14"
    assert detail["per_diem"]["total_pln"] == "562.28"


@pytest.mark.asyncio
async def test_without_a_rate_the_per_diem_stays_in_its_own_currency(
    db_session: AsyncSession,
) -> None:
    user = await UserFactory.create_async()
    trip = (
        await _call(db_session, user, "POST", "/api/v1/trips", json=_trip("business", 13, 15))
    ).json()

    given = await _call(
        db_session, user, "PUT", f"/api/v1/trips/{trip['id']}/per-diem", json=_times()
    )

    assert (given.json()["parts"][0]["total"], given.json()["total_pln"]) == ("132.30", None)


@pytest.mark.asyncio
async def test_a_per_diem_is_refused_for_a_personal_trip_and_for_times_out_of_order(
    db_session: AsyncSession,
) -> None:
    user = await UserFactory.create_async()
    personal = (
        await _call(db_session, user, "POST", "/api/v1/trips", json=_trip("personal", 1, 3))
    ).json()
    business = (
        await _call(db_session, user, "POST", "/api/v1/trips", json=_trip("business", 13, 15))
    ).json()

    on_holiday = await _call(
        db_session, user, "PUT", f"/api/v1/trips/{personal['id']}/per-diem", json=_times()
    )
    backwards = await _call(
        db_session,
        user,
        "PUT",
        f"/api/v1/trips/{business['id']}/per-diem",
        json=_times(returned="2026-10-12T21:00:00+02:00"),
    )
    no_offset = await _call(
        db_session,
        user,
        "PUT",
        f"/api/v1/trips/{business['id']}/per-diem",
        json=_times(departure="2026-10-13T06:00:00"),
    )

    assert (on_holiday.status_code, on_holiday.json()["code"]) == (422, "per_diem_personal_trip")
    assert (backwards.status_code, backwards.json()["code"]) == (422, "per_diem_times")
    assert no_offset.status_code == 422


@pytest.mark.asyncio
async def test_forgetting_the_times_takes_the_per_diem_away(db_session: AsyncSession) -> None:
    user = await UserFactory.create_async()
    trip = (
        await _call(db_session, user, "POST", "/api/v1/trips", json=_trip("business", 13, 15))
    ).json()
    await _call(db_session, user, "PUT", f"/api/v1/trips/{trip['id']}/per-diem", json=_times())

    forgotten = await _call(db_session, user, "DELETE", f"/api/v1/trips/{trip['id']}/per-diem")
    detail = (await _call(db_session, user, "GET", f"/api/v1/trips/{trip['id']}")).json()

    assert (forgotten.status_code, detail["per_diem"]) == (204, None)


@pytest.mark.asyncio
async def test_another_users_trip_times_are_out_of_reach(db_session: AsyncSession) -> None:
    """N2."""
    owner, intruder = await UserFactory.create_async(), await UserFactory.create_async()
    trip = (
        await _call(db_session, owner, "POST", "/api/v1/trips", json=_trip("business", 13, 15))
    ).json()

    given = await _call(
        db_session, intruder, "PUT", f"/api/v1/trips/{trip['id']}/per-diem", json=_times()
    )

    assert given.status_code == 404


def _png() -> bytes:
    out = io.BytesIO()
    Image.new("RGB", (40, 60), "white").save(out, format="PNG")
    return out.getvalue()


class _Photos:
    """Object storage as a stub: every receipt photo is one small picture."""

    def __init__(self) -> None:
        self.uploaded: dict[str, bytes] = {}

    async def download_file(self, object_name: str) -> bytes:
        return _png()

    async def upload_file(self, object_name: str, content: bytes, content_type: str) -> None:
        self.uploaded[object_name] = content


async def _business_trip_with_receipts(session: AsyncSession, user: User) -> str:
    """The F20.5 demo: Berlin, a 612.40 receipt put in by hand, times given, 500 advance."""
    berlin = await _receipt(session, user.id, 14, "612.40", file_ids=["photo-1"])
    trip = (
        await _call(
            session,
            user,
            "POST",
            "/api/v1/trips",
            json={
                **_trip("business", 13, 15, "Berlin"),
                "advance": "500.00",
                "advance_paid_on": "2026-10-10",
            },
        )
    ).json()
    await _answer(session, user, berlin.id, trip["id"])
    await _call(session, user, "PUT", f"/api/v1/trips/{trip['id']}/per-diem", json=_times())
    return str(trip["id"])


@pytest.mark.asyncio
async def test_a_business_trip_says_what_is_left_to_reimburse(db_session: AsyncSession) -> None:
    """F20.5: expenses + per diem - advance, the per diem at the advance day's NBP rate."""
    user = await UserFactory.create_async(currency="PLN")
    trip_id = await _business_trip_with_receipts(db_session, user)

    detail = (
        await _call(db_session, user, "GET", f"/api/v1/trips/{trip_id}", rates=_EuroAt425())
    ).json()

    assert detail["settlement"] == {
        "currency": "PLN",
        "expenses": "612.40",
        "per_diem": "562.28",
        "advance": "500.00",
        "to_reimburse": "674.68",
    }
    assert detail["per_diem"]["to_pln"][0]["effective_date"] == "2026-10-10"


@pytest.mark.asyncio
async def test_a_personal_trip_takes_no_advance_and_has_nothing_to_settle(
    db_session: AsyncSession,
) -> None:
    user = await UserFactory.create_async()
    refused = await _call(
        db_session,
        user,
        "POST",
        "/api/v1/trips",
        json={**_trip("personal", 1, 3), "advance": "100.00"},
    )
    trip = await _call(db_session, user, "POST", "/api/v1/trips", json=_trip("personal", 1, 3))
    detail = (await _call(db_session, user, "GET", f"/api/v1/trips/{trip.json()['id']}")).json()

    assert refused.status_code == 422
    assert detail["settlement"] is None


@pytest.mark.asyncio
async def test_a_settlement_is_written_as_pdf_with_its_photos_and_as_csv(
    db_session: AsyncSession,
) -> None:
    """F20.5: the summary, then the receipts' photos; the CSV in the user's language."""
    user = await UserFactory.create_async(currency="PLN", language="pl")
    trip_id = await _business_trip_with_receipts(db_session, user)
    storage = _Photos()
    current_user_id.set(user.id)
    jobs = []
    for fmt in (ExportFormat.PDF, ExportFormat.CSV):
        job = ExportJob(
            user_id=user.id,
            kind=ExportKind.TRIP,
            format=fmt,
            params={"trip_id": trip_id, "language": "pl"},
            filename=f"trip-settlement.{fmt.value}",
        )
        db_session.add(job)
        await db_session.flush()
        await ExportService(db_session, cast(StoragePort, storage), _EuroAt425()).write(job)
        jobs.append(job)

    pdf = storage.uploaded[str(jobs[0].object_name)]
    csv_text = storage.uploaded[str(jobs[1].object_name)].decode("utf-8")
    assert pdf.startswith(b"%PDF")
    assert len(re.findall(rb"/Type\s*/Page\b", pdf)) == 2  # the summary, and the one photo
    assert "Do zwrotu pracownikowi,,,,674.68,PLN" in csv_text
    assert "Paragony,2026-10-14,Shop,Inne,612.40,PLN,612.40,PLN" in csv_text


@pytest.mark.asyncio
async def test_a_settlement_export_is_for_ones_own_business_trip_only(
    db_session: AsyncSession,
) -> None:
    """N2, and a settlement is never JSON nor anything else a PDF."""
    owner, intruder = await UserFactory.create_async(), await UserFactory.create_async()
    trip_id = await _business_trip_with_receipts(db_session, owner)
    personal = (
        await _call(db_session, owner, "POST", "/api/v1/trips", json=_trip("personal", 1, 3))
    ).json()

    with patch("app.api.routers.exports.run_export", new=AsyncMock()) as run:
        mine = await _call(
            db_session,
            owner,
            "POST",
            "/api/v1/exports",
            json={"kind": "trip", "format": "pdf", "trip_id": trip_id},
        )
        theirs = await _call(
            db_session,
            intruder,
            "POST",
            "/api/v1/exports",
            json={"kind": "trip", "format": "pdf", "trip_id": trip_id},
        )
        holiday = await _call(
            db_session,
            owner,
            "POST",
            "/api/v1/exports",
            json={"kind": "trip", "format": "csv", "trip_id": personal["id"]},
        )
        receipts_pdf = await _call(
            db_session, owner, "POST", "/api/v1/exports", json={"kind": "receipts", "format": "pdf"}
        )

    assert (mine.status_code, mine.json()["filename"]) == (
        202,
        "trip-settlement-2026-10-13_2026-10-15.pdf",
    )
    assert run.await_count == 1
    assert (theirs.status_code, holiday.status_code) == (404, 404)
    assert (receipts_pdf.status_code, receipts_pdf.json()["code"]) == (422, "invalid_export")


async def _expense(
    session: AsyncSession, user: User, rates: ExchangeRatePort | None = None, **fields: Any
) -> Response:
    """Type in an expense without a receipt: a 120 PLN tour paid in cash on 3 October."""
    dining = await _builtin(session, "Entertainment")
    return await _call(
        session,
        user,
        "POST",
        "/receipts/manual",
        rates=rates,
        json={
            "description": "Pyramids tour",
            "spent_on": "2026-10-03",
            "amount": "120.00",
            "category_id": str(dining.id),
            **fields,
        },
    )


@pytest.mark.asyncio
async def test_an_expense_without_a_receipt_counts_like_one(db_session: AsyncSession) -> None:
    """F20.5: cash for a tour is in the month and joins the trip its day falls in."""
    user = await UserFactory.create_async(currency="PLN")
    trip = (
        await _call(
            db_session, user, "POST", "/api/v1/trips", json=_trip("personal", 1, 8, "Egypt")
        )
    ).json()

    added = await _expense(db_session, user)
    month = await _dashboard(db_session, user)
    detail = (await _call(db_session, user, "GET", f"/api/v1/trips/{trip['id']}")).json()

    assert added.status_code == 201, added.json()
    body = added.json()
    assert (body["channel"], body["status"], body["total_amount"]) == ("manual", "parsed", "120.00")
    assert body["line_items"][0]["category"]["name"] == "Entertainment"
    assert body["trip"]["name"] == "Egypt"
    assert month["summary"]["total"] == "120.00"
    assert (detail["receipt_count"], detail["total"]) == (1, "120.00")


@pytest.mark.asyncio
async def test_a_foreign_expense_without_a_receipt_is_converted(db_session: AsyncSession) -> None:
    user = await UserFactory.create_async(currency="PLN")

    added = await _expense(db_session, user, rates=_EuroAt425(), currency="EUR", amount="20.00")

    body = added.json()
    assert (body["total_amount"], body["original_total"], body["original_currency"]) == (
        "85.00",
        "20.00",
        "EUR",
    )


@pytest.mark.asyncio
async def test_an_expense_typed_in_on_a_business_trip_goes_where_the_user_said(
    db_session: AsyncSession,
) -> None:
    """The same choice as the wizard's: the company's, or the user's own."""
    user = await UserFactory.create_async()
    trip = (
        await _call(db_session, user, "POST", "/api/v1/trips", json=_trip("business", 1, 8))
    ).json()

    theirs = await _expense(db_session, user, trip_chosen=True, trip_id=trip["id"])
    mine = await _expense(db_session, user, trip_chosen=True, trip_id=None)
    asked = await _expense(db_session, user)

    assert theirs.json()["trip"]["id"] == trip["id"]
    assert (mine.json()["trip"], mine.json()["trip_question"]) == (None, None)
    assert asked.json()["trip_question"]["id"] == trip["id"]


@pytest.mark.asyncio
async def test_an_expense_typed_in_is_never_counted_as_a_reading(
    db_session: AsyncSession,
) -> None:
    """F15.4's accuracy report is about what the model read; nothing was read here."""
    user = await UserFactory.create_async()
    await _expense(db_session, user)

    readings = await ReceiptRepository(db_session).readings_since(
        user.id, datetime(2026, 1, 1, tzinfo=UTC)
    )

    assert readings == []


@pytest.mark.asyncio
async def test_another_users_category_or_trip_cannot_take_an_expense(
    db_session: AsyncSession,
) -> None:
    """N2."""
    owner, intruder = await UserFactory.create_async(), await UserFactory.create_async()
    trip = (
        await _call(db_session, owner, "POST", "/api/v1/trips", json=_trip("business", 1, 8))
    ).json()
    their_category = await CategoryFactory.create_async(user_id=owner.id, name="Owner's own")

    into_their_trip = await _expense(db_session, intruder, trip_chosen=True, trip_id=trip["id"])
    their_category_used = await _call(
        db_session,
        intruder,
        "POST",
        "/receipts/manual",
        json={
            "description": "Taxi",
            "spent_on": "2026-10-03",
            "amount": "10.00",
            "category_id": str(their_category.id),
        },
    )

    assert (into_their_trip.status_code, their_category_used.status_code) == (404, 404)


@pytest.mark.asyncio
async def test_a_settlement_marks_an_expense_without_a_receipt(db_session: AsyncSession) -> None:
    """F20.5: the employer sees which line has no document; no photo page is made for it."""
    user = await UserFactory.create_async(currency="PLN", language="pl")
    trip_id = await _business_trip_with_receipts(db_session, user)
    await _expense(
        db_session,
        user,
        description="Parking",
        spent_on="2026-10-14",
        amount="12.00",
        trip_chosen=True,
        trip_id=trip_id,
    )
    storage = _Photos()
    current_user_id.set(user.id)
    job = ExportJob(
        user_id=user.id,
        kind=ExportKind.TRIP,
        format=ExportFormat.CSV,
        params={"trip_id": trip_id, "language": "pl"},
        filename="trip-settlement.csv",
    )
    db_session.add(job)
    await db_session.flush()

    await ExportService(db_session, cast(StoragePort, storage), _EuroAt425()).write(job)

    csv_text = storage.uploaded[str(job.object_name)].decode("utf-8")
    assert "Parking (bez paragonu)" in csv_text


@pytest.mark.asyncio
async def test_a_settlement_after_90_days_is_the_summary_and_marks_the_removed_photo(
    db_session: AsyncSession,
) -> None:
    """F17.9.3: the totals stand, no page for a photo storage removed, no placeholder."""
    user = await UserFactory.create_async(currency="PLN", language="pl")
    trip_id = await _business_trip_with_receipts(db_session, user)
    receipt = await db_session.scalar(select(Receipt).where(Receipt.user_id == user.id))
    assert receipt is not None
    receipt.created_at = datetime.now(UTC) - timedelta(days=100)
    await db_session.flush()
    storage = _Photos()
    current_user_id.set(user.id)
    jobs = []
    for fmt in (ExportFormat.PDF, ExportFormat.CSV):
        job = ExportJob(
            user_id=user.id,
            kind=ExportKind.TRIP,
            format=fmt,
            params={"trip_id": trip_id, "language": "pl"},
            filename=f"trip-settlement.{fmt.value}",
        )
        db_session.add(job)
        await db_session.flush()
        await ExportService(db_session, cast(StoragePort, storage), _EuroAt425()).write(job)
        jobs.append(job)
    detail = (
        await _call(db_session, user, "GET", f"/api/v1/trips/{trip_id}", rates=_EuroAt425())
    ).json()

    pdf = storage.uploaded[str(jobs[0].object_name)]
    csv_text = storage.uploaded[str(jobs[1].object_name)].decode("utf-8")
    assert len(re.findall(rb"/Type\s*/Page\b", pdf)) == 1
    assert "Shop (zdjęcie usunięte po 90 dniach)" in csv_text
    assert "Do zwrotu pracownikowi,,,,674.68,PLN" in csv_text
    assert detail["receipts"][0]["photos_removed"] is True
    assert detail["photos_expire_on"] is None


@pytest.mark.asyncio
async def test_a_trip_says_when_its_first_kept_photo_will_be_removed(
    db_session: AsyncSession,
) -> None:
    """F17.9.3: the warning that the settlement's photos will not be kept forever."""
    user = await UserFactory.create_async(currency="PLN")
    trip_id = await _business_trip_with_receipts(db_session, user)
    receipt = await db_session.scalar(select(Receipt).where(Receipt.user_id == user.id))
    assert receipt is not None

    detail = (
        await _call(db_session, user, "GET", f"/api/v1/trips/{trip_id}", rates=_EuroAt425())
    ).json()

    assert (
        detail["photos_expire_on"] == (receipt.created_at + timedelta(days=90)).date().isoformat()
    )
