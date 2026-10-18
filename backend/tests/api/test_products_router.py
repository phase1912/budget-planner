"""The products list, merge and split over HTTP (F16.1, N2)."""

import uuid
from collections.abc import AsyncGenerator
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
    session: AsyncSession, user: User, method: str, path: str, json: Any = None
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
        return await client.request(method, f"/api/v1/products{path}", json=json)


async def _bought(session: AsyncSession, user_id: uuid.UUID, shop: str, name: str) -> None:
    session.add(
        Receipt(
            id=uuid.uuid4(),
            user_id=user_id,
            merchant_name=shop,
            total_amount=Decimal("4.99"),
            status=ReceiptStatus.PARSED,
            file_ids=[],
            line_items=[
                LineItem(
                    id=uuid.uuid4(),
                    name=name,
                    quantity=Decimal(1),
                    unit_price=Decimal("4.99"),
                    total_price=Decimal("4.99"),
                )
            ],
        )
    )
    await session.flush()


@pytest.mark.asyncio
async def test_the_list_merge_and_split_answer_with_the_callers_products(
    db_session: AsyncSession,
) -> None:
    user = await UserFactory.create_async()
    await _bought(db_session, user.id, "Biedronka", "Jajko Niespodzianka 20g")
    await _bought(db_session, user.id, "Lidl", "Kinder Joy 20g")

    listed = (await _call(db_session, user, "GET", "")).json()
    egg, joy = sorted(listed, key=lambda p: p["name"])
    merged = await _call(
        db_session, user, "POST", f"/{egg['id']}/merge", {"product_ids": [joy["id"]]}
    )
    alias = next(v for v in merged.json()[0]["variants"] if v["printed_name"] == "Kinder Joy 20g")
    split = await _call(
        db_session, user, "POST", f"/{egg['id']}/split", {"alias_id": alias["alias_id"]}
    )

    assert [(p["name"], p["purchases"], p["shops"]) for p in merged.json()] == [
        ("Jajko Niespodzianka 20g", 2, 2)
    ]
    assert sorted(p["name"] for p in split.json()) == ["Jajko Niespodzianka 20g", "Kinder Joy 20g"]


@pytest.mark.asyncio
async def test_another_users_product_is_not_found(db_session: AsyncSession) -> None:
    """N2: neither listed nor merged into."""
    owner, intruder = await UserFactory.create_async(), await UserFactory.create_async()
    await _bought(db_session, owner.id, "Biedronka", "Chleb 300g")
    await _bought(db_session, intruder.id, "Biedronka", "Bulka 80g")
    theirs = (await _call(db_session, owner, "GET", "")).json()[0]
    mine = (await _call(db_session, intruder, "GET", "")).json()[0]

    response = await _call(
        db_session, intruder, "POST", f"/{mine['id']}/merge", {"product_ids": [theirs["id"]]}
    )

    assert response.status_code == 404
    assert [p["name"] for p in (await _call(db_session, intruder, "GET", "")).json()] == [
        "Bulka 80g"
    ]


@pytest.mark.asyncio
async def test_the_overview_ranks_the_callers_shops_and_ignores_others(
    db_session: AsyncSession,
) -> None:
    user = await UserFactory.create_async()
    stranger = await UserFactory.create_async()
    await _bought(db_session, user.id, "Lidl", "Mleko 1l")
    await _bought(db_session, stranger.id, "Żabka", "Mleko 1l")

    overview = await _call(db_session, user, "GET", "/overview")

    assert overview.status_code == 200
    assert overview.json() == {"moves": [], "shops": [], "paid_above": "0"}
