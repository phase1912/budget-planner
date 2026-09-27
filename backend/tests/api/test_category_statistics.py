"""Category statistics over a period, against a real database (F7.1, BRD E1, E4, N2)."""

import uuid
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
from app.models.receipt import ReceiptStatus
from app.models.user import User
from tests.api.test_budget_router import _receipt
from tests.factories.user import UserFactory

GROCERIES = uuid.UUID("00000000-0000-0000-0000-000000000001")
DINING = uuid.UUID("00000000-0000-0000-0000-000000000002")


async def _statistics(
    session: AsyncSession, user: User, start: str, end: str, *, compare: bool = False
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
        return await client.get(
            "/api/v1/statistics/categories",
            params={"start": start, "end": end, "compare": str(compare).lower()},
        )


async def _bought(
    session: AsyncSession,
    user: User,
    when: datetime | None,
    lines: list[tuple[str, uuid.UUID]],
    **kwargs: Any,
) -> None:
    receipt = await _receipt(session, user, when, [a for a, _ in lines], **kwargs)  # type: ignore[arg-type]
    for line, (_, category) in zip(receipt.line_items, lines, strict=True):
        line.category_id = category
    await session.flush()


def _rows(body: dict[str, Any]) -> list[tuple[str, str, str, int]]:
    return [(c["name"], c["total"], c["share"], c["item_count"]) for c in body["categories"]]


@pytest.mark.asyncio
async def test_each_category_comes_with_its_total_share_and_items_biggest_first(
    db_session: AsyncSession,
) -> None:
    """E1, E4: a July with more spent on groceries than dining ranks groceries first."""
    user = await UserFactory.create_async()
    await _bought(
        db_session,
        user,
        datetime(2026, 7, 3, tzinfo=UTC),
        [("30.00", DINING), ("45.00", GROCERIES)],
    )
    await _bought(db_session, user, datetime(2026, 7, 20, tzinfo=UTC), [("25.00", GROCERIES)])

    response = await _statistics(db_session, user, "2026-07-01", "2026-07-31")

    assert response.status_code == 200, response.json()
    body = response.json()
    assert _rows(body) == [("Groceries", "70.00", "70.0", 2), ("Dining", "30.00", "30.0", 1)]
    assert (body["total"], body["item_count"]) == ("100.00", 3)


@pytest.mark.asyncio
async def test_both_ends_of_the_period_are_included_and_nothing_beyond(
    db_session: AsyncSession,
) -> None:
    user = await UserFactory.create_async()
    await _bought(db_session, user, datetime(2026, 7, 10, 0, 0, tzinfo=UTC), [("1.00", DINING)])
    await _bought(db_session, user, datetime(2026, 7, 24, 23, 59, tzinfo=UTC), [("2.00", DINING)])
    await _bought(db_session, user, datetime(2026, 7, 9, 23, 59, tzinfo=UTC), [("40.00", DINING)])
    await _bought(db_session, user, datetime(2026, 7, 25, 0, 0, tzinfo=UTC), [("80.00", DINING)])

    body = (await _statistics(db_session, user, "2026-07-10", "2026-07-24")).json()

    assert _rows(body) == [("Dining", "3.00", "100.0", 2)]


@pytest.mark.asyncio
async def test_receipts_under_review_are_left_out_but_named(db_session: AsyncSession) -> None:
    """D3: the figures never quietly miss what could not be read."""
    user = await UserFactory.create_async()
    await _bought(db_session, user, datetime(2026, 7, 3, tzinfo=UTC), [("10.00", GROCERIES)])
    await _bought(
        db_session,
        user,
        None,
        [("99.00", GROCERIES)],
        status=ReceiptStatus.MANUAL_REVIEW,
        uploaded=datetime(2026, 7, 15, tzinfo=UTC),
    )

    body = (await _statistics(db_session, user, "2026-07-01", "2026-07-31")).json()

    assert _rows(body) == [("Groceries", "10.00", "100.0", 1)]
    assert (body["excluded_count"], Decimal(body["excluded_amount"])) == (1, Decimal("99.00"))


@pytest.mark.asyncio
async def test_another_users_spending_never_appears(db_session: AsyncSession) -> None:
    """BRD N2."""
    owner = await UserFactory.create_async()
    stranger = await UserFactory.create_async()
    await _bought(db_session, stranger, datetime(2026, 7, 3, tzinfo=UTC), [("500.00", DINING)])

    body = (await _statistics(db_session, owner, "2026-07-01", "2026-07-31")).json()

    assert body["categories"] == []
    assert (Decimal(body["total"]), body["item_count"]) == (Decimal(0), 0)


@pytest.mark.asyncio
async def test_a_period_ending_before_it_starts_is_refused(db_session: AsyncSession) -> None:
    user = await UserFactory.create_async()

    response = await _statistics(db_session, user, "2026-07-24", "2026-07-10")

    assert response.status_code == 422
    assert response.json()["code"] == "invalid_period"


@pytest.mark.asyncio
async def test_a_purchase_in_the_last_second_of_the_last_day_is_still_inside(
    db_session: AsyncSession,
) -> None:
    """E2: the end day is included whole — up to midnight, not up to 23:59:59."""
    user = await UserFactory.create_async()
    late = datetime(2026, 7, 24, 23, 59, 59, 500000, tzinfo=UTC)
    await _bought(db_session, user, late, [("4.00", DINING)])

    body = (await _statistics(db_session, user, "2026-07-10", "2026-07-24")).json()

    assert _rows(body) == [("Dining", "4.00", "100.0", 1)]


@pytest.mark.asyncio
async def test_a_list_given_only_one_end_of_a_period_is_refused(db_session: AsyncSession) -> None:
    """A half-given range is a mistake, not "from then on": the same rule as statistics."""
    user = await UserFactory.create_async()

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db_session] = override_get_db
    current_user_id.set(user.id)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        receipts = await client.get("/receipts", params={"start": "2026-07-10"})
        items = await client.get("/receipts/line-items", params={"end": "2026-07-10"})

    assert (receipts.status_code, items.status_code) == (422, 422)
    assert receipts.json()["code"] == "invalid_period"


@pytest.mark.asyncio
async def test_a_running_month_is_compared_with_the_same_days_of_the_month_before(
    db_session: AsyncSession,
) -> None:
    """E3, D4: 1-27 July against 1-27 June, never the whole of June."""
    user = await UserFactory.create_async()
    await _bought(db_session, user, datetime(2026, 7, 5, tzinfo=UTC), [("60.00", GROCERIES)])
    await _bought(db_session, user, datetime(2026, 6, 5, tzinfo=UTC), [("80.00", GROCERIES)])
    await _bought(db_session, user, datetime(2026, 6, 10, tzinfo=UTC), [("25.00", DINING)])
    await _bought(db_session, user, datetime(2026, 6, 28, tzinfo=UTC), [("500.00", GROCERIES)])

    body = (await _statistics(db_session, user, "2026-07-01", "2026-07-27", compare=True)).json()

    assert body["comparison"] == {
        "start": "2026-06-01",
        "end": "2026-06-27",
        "total": "105.00",
        "item_count": 2,
        "stops_mid_month": True,
    }
    rows = [
        (c["name"], c["total"], c["previous_total"], c["change"], c["change_percent"])
        for c in body["categories"]
    ]
    assert rows == [
        ("Groceries", "60.00", "80.00", "-20.00", "-25.0"),
        ("Dining", "0", "25.00", "-25.00", "-100.0"),
    ]


@pytest.mark.asyncio
async def test_without_asking_there_is_no_comparison(db_session: AsyncSession) -> None:
    user = await UserFactory.create_async()
    await _bought(db_session, user, datetime(2026, 7, 5, tzinfo=UTC), [("60.00", GROCERIES)])

    body = (await _statistics(db_session, user, "2026-07-01", "2026-07-27")).json()

    assert body["comparison"] is None
    assert body["categories"][0]["change"] is None
