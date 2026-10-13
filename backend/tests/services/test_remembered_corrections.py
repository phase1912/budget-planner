"""Corrections that stick: remembered per shop, applied, undone and forgotten (F15.3)."""

import uuid
from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import current_user_id
from app.models.line_item import LineItem
from app.models.receipt import Receipt, ReceiptStatus
from app.models.upload_job import JobStatus
from app.repository.name_correction import NameCorrectionRepository
from app.repository.receipt import ReceiptRepository
from app.schemas.receipt import (
    EditLineItemRequest,
    LineItemInput,
    UndoExtractedCorrectionRequest,
    UpdateReceiptRequest,
)
from app.services.receipt import ReceiptService
from tests.factories.upload_job import UploadJobFactory
from tests.factories.user import UserFactory

PRINTED = "MastoZPolskMlecz200g"


def _extraction(name: str = PRINTED, **line: Any) -> dict[str, Any]:
    return {
        "merchant_name": "Biedronka",
        "receipt_total": "7.49",
        "line_items": [
            {"name": name, "quantity": "1", "unit_price": "7.49", "total_price": "7.49", **line}
        ],
    }


async def _job(user_id: uuid.UUID, extraction: dict[str, Any]) -> uuid.UUID:
    job = await UploadJobFactory.create_async(
        user_id=user_id,
        status=JobStatus.COMPLETED,
        file_ids=[],
        result_data={"extractions": [extraction]},
    )
    return job.id


def _service(db_session: AsyncSession) -> ReceiptService:
    return ReceiptService(repository=ReceiptRepository(db_session))


@pytest.mark.asyncio
async def test_renaming_a_line_in_the_wizard_remembers_it_for_the_shop(
    db_session: AsyncSession,
) -> None:
    user = await UserFactory.create_async()
    job_id = await _job(user.id, _extraction())

    response = await _service(db_session).edit_extracted_line_item(
        job_id, user.id, EditLineItemRequest(extraction_index=0, item_index=0, name="Masło 200g")
    )

    assert response.extracted_data is not None
    line = response.extracted_data["extractions"][0]["line_items"][0]
    assert (line["name"], line["read_name"]) == ("Masło 200g", PRINTED)
    remembered = await NameCorrectionRepository(db_session).list_for(user.id)
    assert [(c.merchant_name, c.read_name, c.corrected_name) for c in remembered] == [
        ("biedronka", "mastozpolskmlecz200g", "Masło 200g")
    ]


@pytest.mark.asyncio
async def test_undoing_a_line_puts_back_what_was_printed_and_keeps_the_memory(
    db_session: AsyncSession,
) -> None:
    user = await UserFactory.create_async()
    corrections = NameCorrectionRepository(db_session)
    await corrections.remember(user.id, "Biedronka", PRINTED, "Masło 200g")
    job_id = await _job(user.id, _extraction("Masło 200g", read_name=PRINTED))

    response = await _service(db_session).undo_extracted_correction(
        job_id, user.id, UndoExtractedCorrectionRequest(extraction_index=0, item_index=0)
    )

    assert response.extracted_data is not None
    line = response.extracted_data["extractions"][0]["line_items"][0]
    assert (line["name"], line["read_name"]) == (PRINTED, None)
    assert len(await corrections.list_for(user.id)) == 1


@pytest.mark.asyncio
async def test_forgetting_a_correction_stops_it_for_later_receipts(
    db_session: AsyncSession,
) -> None:
    user = await UserFactory.create_async()
    corrections = NameCorrectionRepository(db_session)
    await corrections.remember(user.id, "Biedronka", PRINTED, "Masło 200g")
    job_id = await _job(user.id, _extraction("Masło 200g", read_name=PRINTED))

    await _service(db_session).undo_extracted_correction(
        job_id,
        user.id,
        UndoExtractedCorrectionRequest(extraction_index=0, item_index=0, forget=True),
    )

    assert await corrections.list_for(user.id) == []


@pytest.mark.asyncio
async def test_a_line_never_corrected_cannot_be_undone(db_session: AsyncSession) -> None:
    user = await UserFactory.create_async()
    job_id = await _job(user.id, _extraction())

    with pytest.raises(ValueError, match="not corrected"):
        await _service(db_session).undo_extracted_correction(
            job_id, user.id, UndoExtractedCorrectionRequest(extraction_index=0, item_index=0)
        )


async def _stored(db_session: AsyncSession, user_id: uuid.UUID, **line: Any) -> Receipt:
    receipt = Receipt(
        id=uuid.uuid4(),
        user_id=user_id,
        merchant_name="Biedronka",
        total_amount=Decimal("7.49"),
        status=ReceiptStatus.PARSED,
        file_ids=[],
        line_items=[
            LineItem(
                id=uuid.uuid4(),
                quantity=Decimal("1"),
                unit_price=Decimal("7.49"),
                total_price=Decimal("7.49"),
                **{"name": PRINTED, **line},
            )
        ],
    )
    db_session.add(receipt)
    await db_session.flush()
    return receipt


@pytest.mark.asyncio
async def test_renaming_a_stored_line_remembers_it_and_keeps_what_was_printed(
    db_session: AsyncSession,
) -> None:
    user = await UserFactory.create_async()
    current_user_id.set(user.id)
    receipt = await _stored(db_session, user.id)
    line = receipt.line_items[0]

    updated = await _service(db_session).update_receipt(
        receipt.id,
        UpdateReceiptRequest(
            merchant_name="Biedronka",
            transaction_date=None,
            total_amount=Decimal("7.49"),
            line_items=[
                LineItemInput(
                    id=line.id,
                    name="Masło 200g",
                    quantity=line.quantity,
                    unit_price=line.unit_price,
                    total_price=line.total_price,
                )
            ],
        ),
    )

    assert updated is not None
    assert (updated.line_items[0].name, updated.line_items[0].read_name) == ("Masło 200g", PRINTED)
    remembered = await NameCorrectionRepository(db_session).list_for(user.id)
    assert [c.corrected_name for c in remembered] == ["Masło 200g"]


@pytest.mark.asyncio
async def test_undoing_a_stored_line_puts_back_what_was_printed(db_session: AsyncSession) -> None:
    user = await UserFactory.create_async()
    current_user_id.set(user.id)
    receipt = await _stored(db_session, user.id, name="Masło 200g", read_name=PRINTED)

    updated = await _service(db_session).undo_line_correction(
        receipt.id, receipt.line_items[0].id, forget=False
    )

    assert updated is not None
    assert (updated.line_items[0].name, updated.line_items[0].read_name) == (PRINTED, None)


@pytest.mark.asyncio
async def test_another_users_line_cannot_be_undone(db_session: AsyncSession) -> None:
    """N2: someone else's receipt is not found, and its line is left as it was."""
    owner, intruder = await UserFactory.create_async(), await UserFactory.create_async()
    current_user_id.set(owner.id)
    receipt = await _stored(db_session, owner.id, name="Masło 200g", read_name=PRINTED)
    current_user_id.set(intruder.id)

    result = await _service(db_session).undo_line_correction(
        receipt.id, receipt.line_items[0].id, forget=True
    )

    assert result is None
    assert receipt.line_items[0].name == "Masło 200g"


@pytest.mark.asyncio
async def test_one_users_corrections_never_reach_another(db_session: AsyncSession) -> None:
    """N2: corrections are the user's own."""
    owner, other = await UserFactory.create_async(), await UserFactory.create_async()
    corrections = NameCorrectionRepository(db_session)
    await corrections.remember(owner.id, "Biedronka", PRINTED, "Masło 200g")

    assert await corrections.list_for(other.id) == []
