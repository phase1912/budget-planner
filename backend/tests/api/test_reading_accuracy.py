"""The reading-accuracy report, from what users actually corrected (F15.4, N2)."""

import uuid
from collections.abc import AsyncGenerator
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
from app.models.line_item import LineItem
from app.models.receipt import Receipt, ReceiptStatus
from app.models.upload_job import JobStatus
from app.models.user import User
from app.repository.receipt import ReceiptRepository
from app.schemas.receipt import (
    AddDiscountRequest,
    EditLineItemRequest,
    LineItemInput,
    UpdateReceiptRequest,
)
from app.services.receipt import ReceiptService
from tests.factories.upload_job import UploadJobFactory
from tests.factories.user import UserFactory


async def _report(session: AsyncSession, user: User) -> Response:
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
        return await client.get("/api/v1/statistics/reading-accuracy")


def _receipt(user_id: uuid.UUID, merchant: str, *, corrected: bool = False) -> Receipt:
    return Receipt(
        id=uuid.uuid4(),
        user_id=user_id,
        merchant_name=merchant,
        total_amount=Decimal("5.00"),
        status=ReceiptStatus.PARSED,
        file_ids=[],
        user_corrected=corrected,
        line_items=[
            LineItem(
                id=uuid.uuid4(),
                name="Bread",
                quantity=Decimal("1"),
                unit_price=Decimal("5.00"),
                total_price=Decimal("5.00"),
                user_corrected=corrected,
            )
        ],
    )


EXTRACTION: dict[str, Any] = {
    "merchant_name": "Biedronka",
    "receipt_total": "5.00",
    "line_items": [{"name": "Chleb", "quantity": "1", "unit_price": "5.00", "total_price": "5.00"}],
}


@pytest.mark.asyncio
async def test_the_report_counts_the_callers_corrected_receipts_only(
    db_session: AsyncSession,
) -> None:
    """N2: another user's corrections are never in the caller's figures."""
    user, other = await UserFactory.create_async(), await UserFactory.create_async()
    db_session.add_all(
        [
            _receipt(user.id, "Biedronka", corrected=True),
            _receipt(user.id, "Lidl"),
            _receipt(other.id, "Biedronka", corrected=True),
        ]
    )
    await db_session.flush()

    body = (await _report(db_session, user)).json()

    assert (body["receipts"], body["corrected_receipts"]) == (2, 1)
    assert (body["lines"], body["corrected_lines"]) == (2, 1)
    assert body["shops"] == [{"merchant": "Biedronka", "receipts": 1, "corrected": 1}]
    assert len(body["months"]) == 6
    assert body["months"][-1]["receipts"] == 2


@pytest.mark.asyncio
async def test_a_line_fixed_in_the_wizard_is_stored_as_corrected(
    db_session: AsyncSession,
) -> None:
    user = await UserFactory.create_async()
    current_user_id.set(user.id)
    job = await UploadJobFactory.create_async(
        user_id=user.id,
        status=JobStatus.COMPLETED,
        file_ids=[],
        result_data={"extractions": [dict(EXTRACTION)]},
    )
    service = ReceiptService(repository=ReceiptRepository(db_session))
    response = await service.edit_extracted_line_item(
        job.id, user.id, EditLineItemRequest(extraction_index=0, item_index=0, total_price="4.50")
    )
    await service.add_extracted_discount(
        job.id, user.id, AddDiscountRequest(extraction_index=0, amount=Decimal("-0.50"))
    )
    assert response.extracted_data is not None

    extraction = job.result_data["extractions"][0]  # type: ignore[index]
    receipt = ReceiptRepository(db_session).create_from_extraction(
        user_id=user.id, file_ids=[], extraction=extraction, parser_version="1"
    )
    await db_session.flush()

    assert receipt.user_corrected is True
    assert [line.user_corrected for line in receipt.line_items] == [True, True]


@pytest.mark.asyncio
async def test_a_receipt_stored_as_read_is_not_corrected(db_session: AsyncSession) -> None:
    user = await UserFactory.create_async()
    current_user_id.set(user.id)

    receipt = ReceiptRepository(db_session).create_from_extraction(
        user_id=user.id, file_ids=[], extraction=dict(EXTRACTION), parser_version="1"
    )
    await db_session.flush()

    assert receipt.user_corrected is False
    assert receipt.line_items[0].user_corrected is False


@pytest.mark.asyncio
async def test_editing_a_stored_receipt_marks_it_and_the_changed_line(
    db_session: AsyncSession,
) -> None:
    user = await UserFactory.create_async()
    current_user_id.set(user.id)
    receipt = _receipt(user.id, "Biedronka")
    db_session.add(receipt)
    await db_session.flush()
    line = receipt.line_items[0]

    updated = await ReceiptService(repository=ReceiptRepository(db_session)).update_receipt(
        receipt.id,
        UpdateReceiptRequest(
            merchant_name="Biedronka",
            transaction_date=None,
            total_amount=Decimal("4.00"),
            line_items=[
                LineItemInput(
                    id=line.id,
                    name="Bread",
                    quantity=Decimal("1"),
                    unit_price=Decimal("4.00"),
                    total_price=Decimal("4.00"),
                )
            ],
        ),
    )

    assert updated is not None
    assert (updated.user_corrected, updated.line_items[0].user_corrected) == (True, True)


@pytest.mark.asyncio
async def test_saving_a_stored_receipt_unchanged_is_not_a_correction(
    db_session: AsyncSession,
) -> None:
    user = await UserFactory.create_async()
    current_user_id.set(user.id)
    receipt = _receipt(user.id, "Biedronka")
    db_session.add(receipt)
    await db_session.flush()
    line = receipt.line_items[0]

    updated = await ReceiptService(repository=ReceiptRepository(db_session)).update_receipt(
        receipt.id,
        UpdateReceiptRequest(
            merchant_name="Biedronka",
            transaction_date=None,
            total_amount=Decimal("5.00"),
            line_items=[
                LineItemInput(
                    id=line.id,
                    name=line.name,
                    quantity=line.quantity,
                    unit_price=line.unit_price,
                    total_price=line.total_price,
                )
            ],
        ),
    )

    assert updated is not None
    assert updated.user_corrected is False
