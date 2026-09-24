"""The categorisation review queue's query (F5.3, BRD C3, N2)."""

import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime

import jwt
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.core.config import get_settings
from app.core.context import current_user_id
from app.db.session import get_db_session
from app.domain.categories import UNCATEGORIZED, ItemView
from app.main import create_app
from app.models.category import Category
from app.models.line_item import LineItem
from app.models.receipt import Receipt
from app.repository.receipt import ReceiptRepository
from app.schemas.receipt import ReviewQueueItemResponse
from tests.factories.category import CategoryFactory
from tests.factories.line_item import LineItemFactory
from tests.factories.receipt import ReceiptFactory
from tests.factories.user import UserFactory


async def _seeded(db_session: AsyncSession, name: str) -> Category:
    """Fetch a built-in category by name, creating it if the seed is absent.

    Migration `c7dfee8c1b06` seeds these, but migration tests elsewhere in the
    suite round-trip the schema and can leave the table empty by the time we run.
    """
    stmt = select(Category).where(Category.name == name, Category.user_id.is_(None))
    existing = (await db_session.execute(stmt)).scalar_one_or_none()
    return existing or await CategoryFactory.create_async(name=name, user_id=None)


async def _item_on_receipt(
    user_id: uuid.UUID, category: Category, name: str, bought: datetime | None
) -> LineItem:
    receipt = await ReceiptFactory.create_async(
        user_id=user_id, transaction_date=bought, merchant_name="Fresh Market"
    )
    return await LineItemFactory.create_async(receipt=receipt, name=name, category=category)


@pytest.mark.asyncio
async def test_queue_holds_only_uncategorized_items_oldest_purchase_first(
    db_session: AsyncSession,
) -> None:
    user = await UserFactory.create_async()
    current_user_id.set(user.id)
    uncategorized = await _seeded(db_session, UNCATEGORIZED)
    groceries = await _seeded(db_session, "Groceries")

    newer = await _item_on_receipt(
        user.id, uncategorized, "XJ-42", datetime(2026, 7, 20, tzinfo=UTC)
    )
    older = await _item_on_receipt(
        user.id, uncategorized, "Protein Bar XL", datetime(2026, 7, 2, 14, 32, tzinfo=UTC)
    )
    await _item_on_receipt(user.id, groceries, "Bananas", datetime(2026, 7, 1, tzinfo=UTC))

    queue = (await ReceiptRepository(db_session).list_items(ItemView.NEEDS_REVIEW))[0]

    assert [item.id for item in queue] == [older.id, newer.id]


@pytest.mark.asyncio
async def test_queue_item_carries_its_receipt_merchant_and_timed_date(
    db_session: AsyncSession,
) -> None:
    """A receipt stores the printed time, so the response must not demand a bare date."""
    user = await UserFactory.create_async()
    current_user_id.set(user.id)
    uncategorized = await _seeded(db_session, UNCATEGORIZED)
    bought = datetime(2026, 7, 2, 14, 32, tzinfo=UTC)
    await _item_on_receipt(user.id, uncategorized, "Protein Bar XL", bought)

    [item] = (await ReceiptRepository(db_session).list_items(ItemView.NEEDS_REVIEW))[0]
    response = ReviewQueueItemResponse.model_validate(item)

    assert response.merchant_name == "Fresh Market"
    assert response.transaction_date == bought
    assert response.category is not None and response.category.name == UNCATEGORIZED


@pytest.mark.asyncio
async def test_another_users_uncategorized_items_never_reach_my_queue(
    db_session: AsyncSession,
) -> None:
    me = await UserFactory.create_async()
    someone_else = await UserFactory.create_async()
    uncategorized = await _seeded(db_session, UNCATEGORIZED)
    await _item_on_receipt(someone_else.id, uncategorized, "Their item", None)
    current_user_id.set(me.id)

    assert (await ReceiptRepository(db_session).list_items(ItemView.NEEDS_REVIEW))[0] == []


@pytest.mark.asyncio
async def test_review_queue_endpoint_returns_the_receipt_details_over_http(
    db_session: AsyncSession,
) -> None:
    """FastAPI re-validates the response, so the receipt fields must survive that pass too."""
    user = await UserFactory.create_async()
    current_user_id.set(user.id)
    uncategorized = await _seeded(db_session, UNCATEGORIZED)
    await _item_on_receipt(
        user.id, uncategorized, "Protein Bar XL", datetime(2026, 7, 2, 14, 32, tzinfo=UTC)
    )

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db_session] = override_get_db
    token = jwt.encode(
        {"sub": str(user.id)}, get_settings().jwt_secret_key.get_secret_value(), algorithm="HS256"
    )
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {token}"},
    ) as client:
        response = await client.get("/receipts/line-items")

    assert response.status_code == 200
    [item] = response.json()["items"]
    assert item["merchant_name"] == "Fresh Market"
    assert item["transaction_date"].startswith("2026-07-02T14:32")
    assert item["category"]["name"] == UNCATEGORIZED


@pytest.mark.asyncio
async def test_views_split_items_by_whether_they_need_or_got_a_human_decision(
    db_session: AsyncSession,
) -> None:
    user = await UserFactory.create_async()
    current_user_id.set(user.id)
    uncategorized = await _seeded(db_session, UNCATEGORIZED)
    health = await _seeded(db_session, "Health")
    waiting = await _item_on_receipt(user.id, uncategorized, "XJ-42", None)
    waiting.is_category_manual = False
    corrected = await _item_on_receipt(user.id, health, "Protein Bar XL", None)
    corrected.is_category_manual = True
    legacy_receipt = await ReceiptFactory.create_async(user_id=user.id)
    uncategorised_legacy = await LineItemFactory.create_async(
        receipt=legacy_receipt, name="Old item", category=None, is_category_manual=False
    )
    await db_session.flush()
    repo = ReceiptRepository(db_session)

    needs_review = {i.id for i in (await repo.list_items(ItemView.NEEDS_REVIEW))[0]}
    corrected_view = {i.id for i in (await repo.list_items(ItemView.CORRECTED))[0]}
    everything = {i.id for i in (await repo.list_items(ItemView.ALL))[0]}

    assert needs_review == {waiting.id, uncategorised_legacy.id}
    assert corrected_view == {corrected.id}
    assert everything == {waiting.id, corrected.id, uncategorised_legacy.id}
    assert await repo.count_needs_review() == 2


@pytest.mark.asyncio
async def test_search_matches_item_names_and_treats_wildcards_literally(
    db_session: AsyncSession,
) -> None:
    user = await UserFactory.create_async()
    current_user_id.set(user.id)
    health = await _seeded(db_session, "Health")
    bar = await _item_on_receipt(user.id, health, "Protein Bar XL", None)
    discount = await _item_on_receipt(user.id, health, "Discount 100%", None)
    repo = ReceiptRepository(db_session)

    assert [i.id for i in (await repo.list_items(ItemView.ALL, search="protein"))[0]] == [bar.id]
    assert [i.id for i in (await repo.list_items(ItemView.ALL, search="%"))[0]] == [discount.id]


@pytest.mark.asyncio
async def test_a_long_view_is_served_a_page_at_a_time_with_its_total(
    db_session: AsyncSession,
) -> None:
    user = await UserFactory.create_async()
    current_user_id.set(user.id)
    uncategorized = await _seeded(db_session, UNCATEGORIZED)
    items = [
        await _item_on_receipt(
            user.id, uncategorized, f"Item {day}", datetime(2026, 7, day, tzinfo=UTC)
        )
        for day in range(1, 6)
    ]
    repo = ReceiptRepository(db_session)

    first, total = await repo.list_items(ItemView.NEEDS_REVIEW, skip=0, limit=2)
    last, _ = await repo.list_items(ItemView.NEEDS_REVIEW, skip=4, limit=2)

    assert total == 5
    assert [i.id for i in first] == [items[0].id, items[1].id]
    assert [i.id for i in last] == [items[4].id]


@pytest.mark.asyncio
async def test_the_date_filter_uses_the_purchase_date_or_upload_date_when_unread(
    db_session: AsyncSession,
) -> None:
    user = await UserFactory.create_async()
    current_user_id.set(user.id)
    uncategorized = await _seeded(db_session, UNCATEGORIZED)
    june = await _item_on_receipt(user.id, uncategorized, "June", datetime(2026, 6, 30, tzinfo=UTC))
    july = await _item_on_receipt(user.id, uncategorized, "July", datetime(2026, 7, 15, tzinfo=UTC))
    undated = await _item_on_receipt(user.id, uncategorized, "Undated", None)
    receipt = await db_session.get(Receipt, undated.receipt_id)
    assert receipt is not None
    receipt.created_at = datetime(2026, 7, 20, tzinfo=UTC)
    await db_session.flush()

    in_july, total = await ReceiptRepository(db_session).list_items(
        ItemView.ALL,
        start_date=datetime(2026, 7, 1, tzinfo=UTC),
        end_date=datetime(2026, 7, 31, 23, 59, 59, tzinfo=UTC),
    )

    assert [i.id for i in in_july] == [july.id, undated.id]
    assert total == 2
    assert june.id not in {i.id for i in in_july}


@pytest.mark.asyncio
async def test_the_endpoint_reports_paging_and_refuses_oversized_pages(
    db_session: AsyncSession,
) -> None:
    user = await UserFactory.create_async()
    current_user_id.set(user.id)
    uncategorized = await _seeded(db_session, UNCATEGORIZED)
    for day in range(1, 4):
        await _item_on_receipt(
            user.id, uncategorized, f"Item {day}", datetime(2026, 7, day, tzinfo=UTC)
        )

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db_session] = override_get_db
    token = jwt.encode(
        {"sub": str(user.id)}, get_settings().jwt_secret_key.get_secret_value(), algorithm="HS256"
    )
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {token}"},
    ) as client:
        page_two = await client.get("/receipts/line-items?page=2&size=2")
        too_big = await client.get("/receipts/line-items?size=500")

    body = page_two.json()
    assert (body["total"], body["page"], body["size"], body["pages"]) == (3, 2, 2, 2)
    assert [i["name"] for i in body["items"]] == ["Item 3"]
    assert body["needs_review_count"] == 3
    assert too_big.status_code == 422
