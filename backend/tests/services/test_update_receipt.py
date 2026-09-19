"""Correcting a stored receipt's header and line items (F3.9, BRD A9, A11, D6)."""

import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import current_user_id
from app.models.line_item import LineItem
from app.models.receipt import Receipt, ReceiptStatus
from app.repository.receipt import ReceiptRepository
from app.schemas.receipt import LineItemInput, UpdateReceiptRequest
from app.services.receipt import ReceiptService
from tests.factories.user import UserFactory


async def _stored_receipt(db_session: AsyncSession, user_id: uuid.UUID) -> Receipt:
    receipt = Receipt(
        id=uuid.uuid4(),
        user_id=user_id,
        merchant_name="euro sklep",
        transaction_date=None,
        total_amount=Decimal("7.49"),
        status=ReceiptStatus.PARSED,
        file_ids=[],
        line_items=[
            LineItem(
                id=uuid.uuid4(),
                name="MILKA",
                quantity=Decimal("1"),
                unit_price=Decimal("7.49"),
                total_price=Decimal("7.49"),
            )
        ],
    )
    db_session.add(receipt)
    await db_session.flush()
    return receipt


@pytest.mark.asyncio
async def test_correcting_a_price_updates_the_stored_line(db_session: AsyncSession) -> None:
    # Given
    user = await UserFactory.create_async(email="fix-price@example.com")
    current_user_id.set(user.id)
    receipt = await _stored_receipt(db_session, user.id)
    line_id = receipt.line_items[0].id

    service = ReceiptService(repository=ReceiptRepository(db_session))
    request = UpdateReceiptRequest(
        merchant_name="euro sklep",
        transaction_date=date(2026, 9, 13),
        total_amount=Decimal("13.99"),
        line_items=[
            LineItemInput(
                id=line_id,
                name="MILKA",
                quantity=Decimal("1"),
                unit_price=Decimal("13.99"),
                total_price=Decimal("13.99"),
            )
        ],
    )

    # When
    updated = await service.update_receipt(receipt.id, request)

    # Then
    assert updated is not None
    assert updated.total_amount == Decimal("13.99")
    assert len(updated.line_items) == 1
    assert updated.line_items[0].id == line_id
    assert updated.line_items[0].total_price == Decimal("13.99")


@pytest.mark.asyncio
async def test_adding_a_new_line_item_persists_it(db_session: AsyncSession) -> None:
    # Given
    user = await UserFactory.create_async(email="add-line@example.com")
    current_user_id.set(user.id)
    receipt = await _stored_receipt(db_session, user.id)
    existing = receipt.line_items[0]

    service = ReceiptService(repository=ReceiptRepository(db_session))
    request = UpdateReceiptRequest(
        merchant_name="euro sklep",
        transaction_date=None,
        total_amount=Decimal("21.48"),
        line_items=[
            LineItemInput(
                id=existing.id,
                name=existing.name,
                quantity=existing.quantity,
                unit_price=existing.unit_price,
                total_price=existing.total_price,
            ),
            LineItemInput(
                name="AGRO-FARM Jaja",
                quantity=Decimal("10"),
                unit_price=Decimal("13.99"),
                total_price=Decimal("13.99"),
            ),
        ],
    )

    # When
    updated = await service.update_receipt(receipt.id, request)

    # Then
    assert updated is not None
    assert len(updated.line_items) == 2
    new_line = next(i for i in updated.line_items if i.name == "AGRO-FARM Jaja")
    assert new_line.id is not None


@pytest.mark.asyncio
async def test_dropping_a_line_item_deletes_it(db_session: AsyncSession) -> None:
    # Given
    user = await UserFactory.create_async(email="drop-line@example.com")
    current_user_id.set(user.id)
    receipt = await _stored_receipt(db_session, user.id)

    service = ReceiptService(repository=ReceiptRepository(db_session))
    request = UpdateReceiptRequest(
        merchant_name="euro sklep",
        transaction_date=None,
        total_amount=Decimal("0"),
        line_items=[],
    )

    # When
    await service.update_receipt(receipt.id, request)

    # Then
    remaining = await db_session.execute(
        select(func.count()).select_from(LineItem).where(LineItem.receipt_id == receipt.id)
    )
    assert remaining.scalar_one() == 0


@pytest.mark.asyncio
async def test_a_total_that_does_not_match_the_lines_is_refused(db_session: AsyncSession) -> None:
    # Given
    user = await UserFactory.create_async(email="mismatch@example.com")
    current_user_id.set(user.id)
    receipt = await _stored_receipt(db_session, user.id)
    existing = receipt.line_items[0]

    service = ReceiptService(repository=ReceiptRepository(db_session))
    request = UpdateReceiptRequest(
        merchant_name="euro sklep",
        transaction_date=None,
        total_amount=Decimal("999.00"),
        line_items=[
            LineItemInput(
                id=existing.id,
                name=existing.name,
                quantity=existing.quantity,
                unit_price=existing.unit_price,
                total_price=existing.total_price,
            )
        ],
    )

    # When / Then
    updated = await service.update_receipt(receipt.id, request)
    assert updated is not None
    assert updated.status == ReceiptStatus.MANUAL_REVIEW


@pytest.mark.asyncio
async def test_another_users_receipt_cannot_be_updated(db_session: AsyncSession) -> None:
    # Given
    owner = await UserFactory.create_async(email="update-owner@example.com")
    intruder = await UserFactory.create_async(email="update-intruder@example.com")
    current_user_id.set(owner.id)
    receipt = await _stored_receipt(db_session, owner.id)

    current_user_id.set(intruder.id)
    service = ReceiptService(repository=ReceiptRepository(db_session))
    request = UpdateReceiptRequest(
        merchant_name="stolen",
        transaction_date=None,
        total_amount=Decimal("0"),
        line_items=[],
    )

    # When
    result = await service.update_receipt(receipt.id, request)

    # Then
    assert result is None
    current_user_id.set(owner.id)
    intact = await ReceiptRepository(db_session).get(receipt.id)
    assert intact is not None
    assert intact.merchant_name == "euro sklep"


@pytest.mark.asyncio
async def test_a_line_item_id_not_on_the_receipt_is_rejected(db_session: AsyncSession) -> None:
    # Given
    user = await UserFactory.create_async(email="foreign-line@example.com")
    current_user_id.set(user.id)
    receipt = await _stored_receipt(db_session, user.id)

    service = ReceiptService(repository=ReceiptRepository(db_session))
    request = UpdateReceiptRequest(
        merchant_name="euro sklep",
        transaction_date=None,
        total_amount=Decimal("1.00"),
        line_items=[
            LineItemInput(
                id=uuid.uuid4(),
                name="ghost",
                quantity=Decimal("1"),
                unit_price=Decimal("1.00"),
                total_price=Decimal("1.00"),
            )
        ],
    )

    # When / Then
    with pytest.raises(ValueError, match="not found"):
        await service.update_receipt(receipt.id, request)
