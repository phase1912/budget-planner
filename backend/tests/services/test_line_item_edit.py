"""Correcting a line the parser misread is what unblocks storing the receipt.

The commit gate refuses a receipt whose items do not add up, so without this the
user would be stuck looking at a red footer with no way out (BRD A9, A11).
"""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.upload_job import JobStatus
from app.repository.receipt import ReceiptRepository
from app.schemas.receipt import EditLineItemRequest
from app.services.receipt import ReceiptService
from tests.factories.upload_job import UploadJobFactory
from tests.factories.user import UserFactory

EXTRACTION = {
    "merchant_name": "euro sklep",
    "receipt_total": "21,48",
    "line_items": [
        {"name": "MILKA", "quantity": "1", "unit_price": "7,49", "total_price": "7,49"},
        {"name": "AGRO-FARM Jaja", "quantity": "10", "unit_price": "", "total_price": ""},
    ],
}


async def _job(db_session: AsyncSession, email: str) -> tuple[ReceiptService, uuid.UUID, uuid.UUID]:
    user = await UserFactory.create_async(email=email)
    job = await UploadJobFactory.create_async(
        user_id=user.id,
        status=JobStatus.COMPLETED,
        file_ids=[],
        result_data={"extractions": [dict(EXTRACTION)]},
    )
    return ReceiptService(repository=ReceiptRepository(db_session)), job.id, user.id


@pytest.mark.asyncio
async def test_pricing_the_missing_line_makes_the_receipt_add_up(
    db_session: AsyncSession,
) -> None:
    # Given a receipt the parser could not total
    service, job_id, user_id = await _job(db_session, "edit-unblocks@example.com")

    # When the user supplies the price the parser missed
    response = await service.edit_extracted_line_item(
        job_id,
        user_id,
        EditLineItemRequest(extraction_index=0, item_index=1, total_price="13,99"),
    )

    # Then the arithmetic is redone and the commit gate would now let it through
    assert response.extracted_data is not None
    extraction = response.extracted_data["extractions"][0]
    assert extraction["items_sum_matches_total"] is True
    assert extraction["computed_total"] == "21.48"


@pytest.mark.asyncio
async def test_a_field_that_was_not_sent_keeps_its_parsed_value(
    db_session: AsyncSession,
) -> None:
    # Given
    service, job_id, user_id = await _job(db_session, "edit-partial@example.com")

    # When only the price is corrected
    response = await service.edit_extracted_line_item(
        job_id,
        user_id,
        EditLineItemRequest(extraction_index=0, item_index=1, total_price="13,99"),
    )

    # Then the name the parser read is untouched
    assert response.extracted_data is not None
    item = response.extracted_data["extractions"][0]["line_items"][1]
    assert item["name"] == "AGRO-FARM Jaja"
    assert item["quantity"] == "10"


@pytest.mark.asyncio
async def test_an_empty_string_clears_a_price_rather_than_zeroing_it(
    db_session: AsyncSession,
) -> None:
    # Given a line the parser did price
    service, job_id, user_id = await _job(db_session, "edit-clear@example.com")

    # When the user says that price is not really there
    response = await service.edit_extracted_line_item(
        job_id,
        user_id,
        EditLineItemRequest(extraction_index=0, item_index=0, total_price=""),
    )

    # Then it reads as missing, never as zero
    assert response.extracted_data is not None
    item = response.extracted_data["extractions"][0]["line_items"][0]
    assert item["total_price"] == ""


@pytest.mark.asyncio
async def test_another_users_job_cannot_be_edited(db_session: AsyncSession) -> None:
    # Given
    service, job_id, _ = await _job(db_session, "edit-owner@example.com")
    intruder = await UserFactory.create_async(email="edit-intruder@example.com")

    # When / Then
    with pytest.raises(ValueError, match="Job not found"):
        await service.edit_extracted_line_item(
            job_id,
            intruder.id,
            EditLineItemRequest(extraction_index=0, item_index=0, total_price="1,00"),
        )


@pytest.mark.asyncio
async def test_an_item_index_the_receipt_does_not_have_is_rejected(
    db_session: AsyncSession,
) -> None:
    # Given
    service, job_id, user_id = await _job(db_session, "edit-range@example.com")

    # When / Then
    with pytest.raises(ValueError, match="Invalid item index"):
        await service.edit_extracted_line_item(
            job_id,
            user_id,
            EditLineItemRequest(extraction_index=0, item_index=9, total_price="1,00"),
        )
