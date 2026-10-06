"""Adding the discount the reader missed is what makes a Biedronka receipt add up (BRD A9).

The reader sometimes lists every product at full price and skips the "OPUST" lines,
so the lines come to more than was paid. The user adds the gap as one discount.
"""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.upload_job import JobStatus
from app.repository.receipt import ReceiptRepository
from app.schemas.receipt import AddDiscountRequest
from app.services.receipt import ReceiptService
from tests.factories.upload_job import UploadJobFactory
from tests.factories.user import UserFactory

DAIRY = str(uuid.uuid4())
BAKERY = str(uuid.uuid4())

EXTRACTION = {
    "merchant_name": "BIEDRONKA",
    "transaction_date": "2026-10-03",
    "receipt_total": "30,00",
    "line_items": [
        {
            "name": "Masło 200g",
            "quantity": "3",
            "unit_price": "5,99",
            "total_price": "17,97",
            "file_id": "photo-1",
            "category_id": DAIRY,
            "category_name": "Dairy",
            "category_confidence": 95,
        },
        {
            "name": "Jogurt 330ml",
            "quantity": "3",
            "unit_price": "5,49",
            "total_price": "16,47",
            "file_id": "photo-1",
            "category_id": DAIRY,
            "category_name": "Dairy",
            "category_confidence": 95,
        },
        {
            "name": "Chleb",
            "quantity": "1",
            "unit_price": "4,99",
            "total_price": "4,99",
            "file_id": "photo-1",
            "category_id": BAKERY,
            "category_name": "Bakery",
            "category_confidence": 95,
        },
    ],
}


async def _job(db_session: AsyncSession) -> tuple[ReceiptService, uuid.UUID, uuid.UUID]:
    user = await UserFactory.create_async()
    job = await UploadJobFactory.create_async(
        user_id=user.id,
        status=JobStatus.COMPLETED,
        file_ids=[],
        result_data={"extractions": [dict(EXTRACTION)]},
    )
    return ReceiptService(repository=ReceiptRepository(db_session)), job.id, user.id


@pytest.mark.asyncio
async def test_the_missed_discount_makes_the_receipt_add_up_to_what_was_paid(
    db_session: AsyncSession,
) -> None:
    service, job_id, user_id = await _job(db_session)

    response = await service.add_extracted_discount(
        job_id, user_id, AddDiscountRequest(extraction_index=0, amount="-9.43")
    )
    await db_session.flush()  # the JSON column must take what was stored

    assert response.extracted_data is not None
    extraction = response.extracted_data["extractions"][0]
    assert extraction["items_sum_matches_total"] is True
    discount = extraction["line_items"][-1]
    assert (discount["name"], discount["total_price"], discount["file_id"]) == (
        "Rabat",
        "-9.43",
        "photo-1",
    )


@pytest.mark.asyncio
async def test_the_discount_is_filed_where_most_of_the_money_went(
    db_session: AsyncSession,
) -> None:
    """It reduces the bill, not one product, and must not wait in the category queue."""
    service, job_id, user_id = await _job(db_session)

    response = await service.add_extracted_discount(
        job_id, user_id, AddDiscountRequest(extraction_index=0, amount="-9.43")
    )
    await db_session.flush()

    assert response.extracted_data is not None
    discount = response.extracted_data["extractions"][0]["line_items"][-1]
    assert (discount["category_id"], discount["category_name"]) == (DAIRY, "Dairy")


@pytest.mark.asyncio
async def test_another_users_job_cannot_be_given_a_discount(db_session: AsyncSession) -> None:
    """BRD N2: a stranger's job reads as not found."""
    service, job_id, _ = await _job(db_session)
    stranger = await UserFactory.create_async()

    with pytest.raises(ValueError, match="not found"):
        await service.add_extracted_discount(
            job_id, stranger.id, AddDiscountRequest(extraction_index=0, amount="-9.43")
        )


def test_a_discount_must_take_money_off() -> None:
    with pytest.raises(ValueError):
        AddDiscountRequest(extraction_index=0, amount="9.43")
