"""Manual category reassignment over HTTP, against a real database (F5.4, BRD C4, N2)."""

from collections.abc import AsyncGenerator, Sequence
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import jwt
import pytest
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.api.routers.receipts import get_item_categoriser
from app.core.config import get_settings
from app.core.context import current_user_id
from app.db.session import get_db_session
from app.domain.categories import UNCATEGORIZED
from app.main import create_app
from app.models.category import Category
from app.models.line_item import LineItem
from app.models.user import User
from app.schemas.extraction import ExtractedLineItem
from tests.factories.category import CategoryFactory
from tests.factories.line_item import LineItemFactory
from tests.factories.receipt import ReceiptFactory
from tests.factories.user import UserFactory


async def _built_in(session: AsyncSession, name: str) -> Category:
    """A built-in category, created if migration tests have emptied the seed."""
    stmt = select(Category).where(Category.name == name, Category.user_id.is_(None))
    existing = (await session.execute(stmt)).scalar_one_or_none()
    return existing or await CategoryFactory.create_async(name=name, user_id=None)


async def _uncertain_item(owner: User, session: AsyncSession) -> LineItem:
    """An item the agent filed under Uncategorized at 40% confidence."""
    receipt = await ReceiptFactory.create_async(
        user_id=owner.id, transaction_date=datetime(2026, 7, 20, tzinfo=UTC), file_ids=["f1"]
    )
    return await LineItemFactory.create_async(
        receipt=receipt,
        name="Protein Bar XL",
        quantity=Decimal("1"),
        unit_price=Decimal("20.70"),
        total_price=Decimal("20.70"),
        category=await _built_in(session, UNCATEGORIZED),
        category_confidence=40,
        is_category_manual=False,
    )


async def _call(
    session: AsyncSession, user: User, method: str, url: str, json: Any = None
) -> Response:
    """Call the API as `user`, sharing the test's transaction."""

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
        return await client.request(method, url, json=json)


@pytest.mark.asyncio
async def test_owner_reassigns_an_item_and_it_leaves_the_review_queue(
    db_session: AsyncSession,
) -> None:
    owner = await UserFactory.create_async()
    item = await _uncertain_item(owner, db_session)
    health = await _built_in(db_session, "Health")

    response = await _call(
        db_session,
        owner,
        "PATCH",
        f"/receipts/line-items/{item.id}/category",
        {"category_id": str(health.id)},
    )

    assert response.status_code == 200, response.json()
    body = response.json()
    assert body["category"]["name"] == "Health"
    assert body["is_category_manual"] is True
    assert body["category_is_low_confidence"] is False
    # What the agent thought stays on record for auditing it.
    assert body["category_confidence"] == 40

    queue = await _call(db_session, owner, "GET", "/receipts/line-items")
    assert queue.json() == {"items": [], "needs_review_count": 0}


@pytest.mark.asyncio
async def test_another_users_item_cannot_be_reassigned(db_session: AsyncSession) -> None:
    owner = await UserFactory.create_async()
    intruder = await UserFactory.create_async()
    item = await _uncertain_item(owner, db_session)
    health = await _built_in(db_session, "Health")

    response = await _call(
        db_session,
        intruder,
        "PATCH",
        f"/receipts/line-items/{item.id}/category",
        {"category_id": str(health.id)},
    )

    assert response.status_code == 404
    await db_session.refresh(item)
    assert item.is_category_manual is False


@pytest.mark.asyncio
async def test_another_users_custom_category_cannot_be_assigned(
    db_session: AsyncSession,
) -> None:
    owner = await UserFactory.create_async()
    someone_else = await UserFactory.create_async()
    item = await _uncertain_item(owner, db_session)
    their_category = await CategoryFactory.create_async(
        name="Pet Supplies", user_id=someone_else.id
    )

    response = await _call(
        db_session,
        owner,
        "PATCH",
        f"/receipts/line-items/{item.id}/category",
        {"category_id": str(their_category.id)},
    )

    assert response.status_code == 404
    await db_session.refresh(item)
    assert item.is_category_manual is False


@pytest.mark.asyncio
async def test_editing_the_receipt_keeps_a_manual_category(db_session: AsyncSession) -> None:
    """Correcting a receipt's numbers is not an automatic pass: the owner's choice stands."""
    owner = await UserFactory.create_async()
    item = await _uncertain_item(owner, db_session)
    health = await _built_in(db_session, "Health")
    await _call(
        db_session,
        owner,
        "PATCH",
        f"/receipts/line-items/{item.id}/category",
        {"category_id": str(health.id)},
    )

    response = await _call(
        db_session,
        owner,
        "PATCH",
        f"/receipts/{item.receipt_id}",
        {
            "merchant_name": "Fresh Market",
            "transaction_date": "2026-07-20",
            "total_amount": "20.70",
            "line_items": [
                {
                    "id": str(item.id),
                    "name": "Protein Bar XL (renamed)",
                    "quantity": "1",
                    "unit_price": "20.70",
                    "total_price": "20.70",
                }
            ],
        },
    )

    assert response.status_code == 200, response.json()
    [line] = response.json()["line_items"]
    assert line["category"]["name"] == "Health"
    assert line["is_category_manual"] is True


class _ScriptedCategoriser:
    """A substitutable `ItemCategoriserPort` answering by item name; unknown names are declined."""

    def __init__(self, answers: dict[str, tuple[Category, int]]) -> None:
        self.answers = answers
        self.seen: list[str] = []

    async def categorise_items(
        self, items: list[ExtractedLineItem], categories: Sequence[Category]
    ) -> list[ExtractedLineItem]:
        for item in items:
            self.seen.append(item.name)
            if item.name in self.answers:
                category, confidence = self.answers[item.name]
                item.category_id = category.id
                item.category_name = category.name
                item.category_confidence = confidence
        return items


async def _recategorise(
    session: AsyncSession, user: User, receipt_id: Any, categoriser: _ScriptedCategoriser
) -> Response:
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield session

    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db_session] = override_get_db
    app.dependency_overrides[get_item_categoriser] = lambda: categoriser
    token = jwt.encode(
        {"sub": str(user.id)}, get_settings().jwt_secret_key.get_secret_value(), algorithm="HS256"
    )
    current_user_id.set(user.id)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {token}"},
    ) as client:
        return await client.post(f"/receipts/{receipt_id}/categorise")


@pytest.mark.asyncio
async def test_rerunning_categorisation_respects_the_owners_choice(
    db_session: AsyncSession,
) -> None:
    """The F5.4 demo: reassign from the queue, re-run categorisation, the choice survives."""
    owner = await UserFactory.create_async()
    item = await _uncertain_item(owner, db_session)
    health = await _built_in(db_session, "Health")
    groceries = await _built_in(db_session, "Groceries")
    await _call(
        db_session,
        owner,
        "PATCH",
        f"/receipts/line-items/{item.id}/category",
        {"category_id": str(health.id)},
    )
    categoriser = _ScriptedCategoriser({"Protein Bar XL": (groceries, 99)})

    response = await _recategorise(db_session, owner, item.receipt_id, categoriser)

    assert response.status_code == 200, response.json()
    [line] = response.json()["line_items"]
    assert line["category"]["name"] == "Health"
    assert categoriser.seen == []


@pytest.mark.asyncio
async def test_rerunning_categorisation_applies_the_threshold_to_automatic_items(
    db_session: AsyncSession,
) -> None:
    owner = await UserFactory.create_async()
    receipt = await ReceiptFactory.create_async(user_id=owner.id, file_ids=["f1"])
    groceries = await _built_in(db_session, "Groceries")
    await _built_in(db_session, UNCATEGORIZED)
    for name in ("Bananas", "XJ-42"):
        await LineItemFactory.create_async(
            receipt=receipt, name=name, category=None, is_category_manual=False
        )
    categoriser = _ScriptedCategoriser({"Bananas": (groceries, 96), "XJ-42": (groceries, 30)})

    response = await _recategorise(db_session, owner, receipt.id, categoriser)

    assert response.status_code == 200, response.json()
    names = {line["name"]: line["category"]["name"] for line in response.json()["line_items"]}
    assert names == {"Bananas": "Groceries", "XJ-42": UNCATEGORIZED}


@pytest.mark.asyncio
async def test_an_unavailable_categoriser_leaves_the_receipt_untouched(
    db_session: AsyncSession,
) -> None:
    """The port cannot raise: "placed nothing" must neither wipe categories nor claim success."""
    owner = await UserFactory.create_async()
    receipt = await ReceiptFactory.create_async(user_id=owner.id, file_ids=["f1"])
    groceries = await _built_in(db_session, "Groceries")
    await LineItemFactory.create_async(
        receipt=receipt,
        name="Bananas",
        category=groceries,
        category_confidence=96,
        is_category_manual=False,
    )

    response = await _recategorise(db_session, owner, receipt.id, _ScriptedCategoriser({}))

    assert response.status_code == 503
    assert response.json()["code"] == "categoriser_unavailable"
    await db_session.refresh(receipt, ["line_items"])
    assert receipt.line_items[0].category_id == groceries.id


@pytest.mark.asyncio
async def test_another_users_receipt_cannot_be_recategorised(db_session: AsyncSession) -> None:
    owner = await UserFactory.create_async()
    intruder = await UserFactory.create_async()
    item = await _uncertain_item(owner, db_session)

    response = await _recategorise(db_session, intruder, item.receipt_id, _ScriptedCategoriser({}))

    assert response.status_code == 404
