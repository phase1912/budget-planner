import uuid
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import current_user_id
from app.models.line_item import LineItem
from app.models.receipt import Receipt, ReceiptStatus
from app.repository.receipt import ReceiptRepository
from tests.factories.user import UserFactory


@pytest.mark.asyncio
async def test_receipt_repository_get_with_items(db_session: AsyncSession) -> None:
    user = await UserFactory.create_async(email="test1@example.com")
    current_user_id.set(user.id)

    receipt = Receipt(
        id=uuid.uuid4(),
        user_id=user.id,
        merchant_name="A",
        status=ReceiptStatus.UPLOADED,
        file_ids=["1"],
    )
    db_session.add(receipt)
    await db_session.flush()

    item1 = LineItem(
        id=uuid.uuid4(),
        receipt_id=receipt.id,
        name="I1",
        quantity=Decimal(1),
        unit_price=Decimal(1),
        total_price=Decimal(1),
    )
    item2 = LineItem(
        id=uuid.uuid4(),
        receipt_id=receipt.id,
        name="I2",
        quantity=Decimal(1),
        unit_price=Decimal(1),
        total_price=Decimal(1),
    )
    db_session.add(item1)
    db_session.add(item2)
    await db_session.flush()

    repo = ReceiptRepository(db_session)
    fetched_receipt = await repo.get_with_items(receipt.id)

    assert fetched_receipt is not None
    assert fetched_receipt.id == receipt.id
    assert len(fetched_receipt.line_items) == 2


@pytest.mark.asyncio
async def test_receipt_repository_enforces_ownership(db_session: AsyncSession) -> None:
    user = await UserFactory.create_async(email="test2@example.com")
    other_user = await UserFactory.create_async(email="test3@example.com")
    current_user_id.set(user.id)

    receipt = Receipt(
        id=uuid.uuid4(),
        user_id=other_user.id,
        merchant_name="A",
        status=ReceiptStatus.UPLOADED,
        file_ids=["1"],
    )
    db_session.add(receipt)
    await db_session.flush()

    repo = ReceiptRepository(db_session)
    fetched_receipt = await repo.get(receipt.id)

    assert fetched_receipt is None


@pytest.mark.asyncio
async def test_create_from_extraction(db_session: AsyncSession) -> None:
    user = await UserFactory.create_async(email="test_extraction@example.com")
    current_user_id.set(user.id)

    repo = ReceiptRepository(db_session)
    extraction = {
        "merchant_name": "Test Store",
        "transaction_date": "2024-01-01",
        "transaction_time": "12:00",
        "receipt_total": "10.00",
        "requires_manual_review": False,
        "line_items": [
            {
                "name": "Item 1",
                "quantity": "2",
                "unit_price": "5.00",
                "total_price": "10.00",
            }
        ],
    }

    receipt = repo.create_from_extraction(
        user_id=user.id, file_ids=["file_1"], extraction=extraction, parser_version="1.0"
    )

    await db_session.flush()

    fetched = await repo.get_with_items(receipt.id)
    assert fetched is not None
    assert fetched.merchant_name == "Test Store"
    assert fetched.total_amount == Decimal("10.00")
    assert fetched.status == ReceiptStatus.PARSED
    assert len(fetched.line_items) == 1
    assert fetched.line_items[0].name == "Item 1"
    assert fetched.line_items[0].total_price == Decimal("10.00")


@pytest.mark.asyncio
async def test_exists_for_user(db_session: AsyncSession) -> None:
    user = await UserFactory.create_async(email="test_exists@example.com")
    repo = ReceiptRepository(db_session)

    assert not await repo.exists_for_user(user.id)

    current_user_id.set(user.id)
    receipt = Receipt(
        id=uuid.uuid4(),
        user_id=user.id,
        merchant_name="A",
        status=ReceiptStatus.UPLOADED,
        file_ids=["1"],
    )
    db_session.add(receipt)
    await db_session.flush()

    assert await repo.exists_for_user(user.id)


@pytest.mark.asyncio
async def test_has_duplicate(db_session: AsyncSession) -> None:
    import datetime
    import uuid
    from decimal import Decimal

    from app.models.receipt import Receipt, ReceiptStatus
    from app.repository.receipt import ReceiptRepository
    from tests.factories.user import UserFactory

    auth_user = await UserFactory.create_async(email="dup2@example.com")
    repo = ReceiptRepository(db_session)

    # Empty
    assert await repo.has_duplicate(auth_user.id, "Test", "2026-01-01", "100.00") is False

    # Create one
    receipt = Receipt(
        id=uuid.uuid4(),
        user_id=auth_user.id,
        merchant_name="Test Merchant",
        transaction_date=datetime.datetime(2026, 7, 20, tzinfo=datetime.UTC),
        total_amount=Decimal("84.50"),
        status=ReceiptStatus.UPLOADED,
        file_ids=[],
    )
    db_session.add(receipt)
    await db_session.flush()

    # Exact match
    assert await repo.has_duplicate(auth_user.id, "Test Merchant", "2026-07-20", "84.50") is True
    # Different amount
    assert await repo.has_duplicate(auth_user.id, "Test Merchant", "2026-07-20", "84.51") is False
    # Different date
    assert await repo.has_duplicate(auth_user.id, "Test Merchant", "2026-07-21", "84.50") is False
    # Different merchant
    assert await repo.has_duplicate(auth_user.id, "Other", "2026-07-20", "84.50") is False
    # Invalid date string
    assert await repo.has_duplicate(auth_user.id, "Test Merchant", "invalid", "84.50") is False
    # Invalid amount string
    assert await repo.has_duplicate(auth_user.id, "Test Merchant", "2026-07-20", "invalid") is False
