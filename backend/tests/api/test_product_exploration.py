"""Exploring purchases and saved selections over HTTP (F16.2, N2)."""

import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import jwt
import pytest
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.api.routers.products import get_product_matcher
from app.core.config import get_settings
from app.core.context import current_user_id
from app.db.session import get_db_session
from app.main import create_app
from app.models.line_item import LineItem
from app.models.receipt import Receipt, ReceiptStatus
from app.models.user import User
from app.ports.product_matching import MatchQuestion
from tests.factories.user import UserFactory


class NoMatcher:
    async def match(self, questions: list[MatchQuestion]) -> dict[str, str | None]:
        return {q.name: None for q in questions}


async def _call(
    session: AsyncSession, user: User, method: str, path: str, **kwargs: Any
) -> Response:
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield session

    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db_session] = override_get_db
    app.dependency_overrides[get_product_matcher] = NoMatcher
    token = jwt.encode(
        {"sub": str(user.id)}, get_settings().jwt_secret_key.get_secret_value(), algorithm="HS256"
    )
    current_user_id.set(user.id)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {token}"},
    ) as client:
        return await client.request(method, f"/api/v1/products{path}", **kwargs)


async def _bought(
    session: AsyncSession,
    user_id: uuid.UUID,
    shop: str,
    name: str,
    price: str,
    day: datetime,
    status: ReceiptStatus = ReceiptStatus.PARSED,
) -> None:
    session.add(
        Receipt(
            id=uuid.uuid4(),
            user_id=user_id,
            merchant_name=shop,
            transaction_date=day,
            total_amount=Decimal(price),
            status=status,
            file_ids=[],
            line_items=[
                LineItem(
                    id=uuid.uuid4(),
                    name=name,
                    quantity=Decimal(1),
                    unit_price=Decimal(price),
                    total_price=Decimal(price),
                )
            ],
        )
    )
    await session.flush()


async def _products(session: AsyncSession, user: User) -> dict[str, str]:
    listed = (await _call(session, user, "GET", "")).json()
    return {p["name"]: p["id"] for p in listed}


@pytest.mark.asyncio
async def test_a_selection_is_explored_over_a_period_counting_only_counted_receipts(
    db_session: AsyncSession,
) -> None:
    user = await UserFactory.create_async()
    oct_2, oct_5 = datetime(2026, 10, 2, tzinfo=UTC), datetime(2026, 10, 5, tzinfo=UTC)
    await _bought(db_session, user.id, "Biedronka", "Chipsy Lays 140g", "6.99", oct_2)
    await _bought(db_session, user.id, "Zabka", "CHIPSY LAYS 140G", "8.49", oct_5)
    await _bought(db_session, user.id, "Lidl", "Sucharki 150g", "3.49", oct_5)
    await _bought(
        db_session, user.id, "Lidl", "Sucharki 150g", "3.49", datetime(2026, 9, 1, tzinfo=UTC)
    )
    await _bought(
        db_session, user.id, "Lidl", "Sucharki 150g", "9.99", oct_5, ReceiptStatus.MANUAL_REVIEW
    )
    ids = await _products(db_session, user)

    response = await _call(
        db_session,
        user,
        "GET",
        "/explore",
        params={
            "product_ids": [ids["Chipsy Lays 140g"], ids["Sucharki 150g"]],
            "start": "2026-10-01",
            "end": "2026-10-31",
        },
    )

    body = response.json()
    assert response.status_code == 200
    assert (body["totals"]["times"], body["totals"]["spent"]) == (3, "18.97")
    assert body["totals"]["quantities"] == {"g": "430.000"}
    chips = body["products"][0]
    assert [(s["shop"], s["above_percent"]) for s in chips["shops"]] == [
        ("Biedronka", "0.0"),
        ("Zabka", "21.5"),
    ]


@pytest.mark.asyncio
async def test_another_users_product_cannot_be_explored_or_saved(db_session: AsyncSession) -> None:
    """N2: indistinguishable from a product that does not exist."""
    owner, intruder = await UserFactory.create_async(), await UserFactory.create_async()
    day = datetime(2026, 10, 2, tzinfo=UTC)
    await _bought(db_session, owner.id, "Biedronka", "Chleb 300g", "4.00", day)
    theirs = (await _products(db_session, owner))["Chleb 300g"]

    explored = await _call(
        db_session, intruder, "GET", "/explore", params={"product_ids": [theirs]}
    )
    saved = await _call(
        db_session, intruder, "POST", "/selections", json={"name": "Mine", "product_ids": [theirs]}
    )

    assert (explored.status_code, saved.status_code) == (404, 404)


@pytest.mark.asyncio
async def test_a_saved_selection_follows_a_merge_and_another_user_cannot_touch_it(
    db_session: AsyncSession,
) -> None:
    user, other = await UserFactory.create_async(), await UserFactory.create_async()
    day = datetime(2026, 10, 2, tzinfo=UTC)
    await _bought(db_session, user.id, "Biedronka", "Chipsy Lays 140g", "6.99", day)
    await _bought(db_session, user.id, "Lidl", "Crunchips 140g", "5.99", day)
    ids = await _products(db_session, user)
    created = await _call(
        db_session,
        user,
        "POST",
        "/selections",
        json={"name": "Snacks", "product_ids": [ids["Crunchips 140g"]]},
    )
    selection = created.json()

    await _call(
        db_session,
        user,
        "POST",
        f"/{ids['Chipsy Lays 140g']}/merge",
        json={"product_ids": [ids["Crunchips 140g"]]},
    )
    listed = (await _call(db_session, user, "GET", "/selections")).json()
    foreign = await _call(db_session, other, "DELETE", f"/selections/{selection['id']}")
    mine = await _call(db_session, user, "DELETE", f"/selections/{selection['id']}")

    assert created.status_code == 201
    assert listed == [
        {"id": selection["id"], "name": "Snacks", "product_ids": [ids["Chipsy Lays 140g"]]}
    ]
    assert (foreign.status_code, mine.status_code) == (404, 204)


@pytest.mark.asyncio
async def test_the_products_list_says_where_a_product_recently_cost_less(
    db_session: AsyncSession,
) -> None:
    """F16.3: last bought at Zabka, cheaper at Biedronka the week before."""
    user = await UserFactory.create_async()
    now = datetime.now(UTC)
    await _bought(
        db_session, user.id, "Biedronka", "Chipsy Lays 140g", "6.99", now - timedelta(days=7)
    )
    await _bought(db_session, user.id, "Zabka", "Chipsy Lays 140g", "8.49", now - timedelta(days=1))
    await _bought(db_session, user.id, "Lidl", "Sucharki 150g", "3.49", now - timedelta(days=1))

    listed = {p["name"]: p for p in (await _call(db_session, user, "GET", "")).json()}

    assert listed["Chipsy Lays 140g"]["cheaper"] == {
        "shop": "Biedronka",
        "instead_of": "Zabka",
        "difference": "1.50",
        "percent": "17.7",
    }
    assert listed["Sucharki 150g"]["cheaper"] is None
