"""Deleting a receipt must take its line items and its photos with it.

Nothing else in the codebase removes objects from storage, so a receipt whose
row is gone would otherwise leave its images behind forever.
"""

import uuid

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import current_user_id
from app.models.line_item import LineItem
from app.models.receipt import Receipt, ReceiptStatus
from app.models.upload_job import JobStatus
from app.ports.storage import StoragePort
from app.repository.receipt import ReceiptRepository
from app.services.receipt import ReceiptService, receipt_object_name
from tests.factories.upload_job import UploadJobFactory
from tests.factories.user import UserFactory


class RecordingStoragePort(StoragePort):
    """Storage double that remembers which keys it was asked to delete.

    Subclasses the port so it stays substitutable for the real client, which is
    what the other methods inherit their no-op bodies for.
    """

    def __init__(self, fail_on: str | None = None) -> None:
        self.deleted: list[str] = []
        self.fail_on = fail_on

    async def delete_file(self, object_name: str) -> None:
        if object_name == self.fail_on:
            raise RuntimeError("storage is down")
        self.deleted.append(object_name)

    async def upload_file(
        self,
        object_name: str,
        content: bytes,
        content_type: str,
        metadata: dict[str, str] | None = None,
    ) -> str:
        return object_name

    async def get_object_metadata(self, object_name: str) -> dict[str, str]:
        return {}

    async def generate_presigned_url(self, object_name: str, expiration_seconds: int = 3600) -> str:
        return f"https://mock-s3.local/{object_name}"

    async def download_file(self, object_name: str) -> bytes:
        return b"fake-image-data"


async def _receipt_with_photos(
    db_session: AsyncSession, user_id: uuid.UUID, file_ids: list[str]
) -> Receipt:
    receipt = Receipt(
        id=uuid.uuid4(),
        user_id=user_id,
        merchant_name="euro sklep",
        status=ReceiptStatus.PARSED,
        file_ids=file_ids,
    )
    db_session.add(receipt)
    await db_session.flush()
    return receipt


@pytest.mark.asyncio
async def test_deleting_a_receipt_removes_every_one_of_its_photos(
    db_session: AsyncSession,
) -> None:
    # Given
    user = await UserFactory.create_async(email="delete-photos@example.com")
    current_user_id.set(user.id)
    receipt = await _receipt_with_photos(db_session, user.id, ["photo-a", "photo-b"])

    storage = RecordingStoragePort()
    service = ReceiptService(storage_port=storage, repository=ReceiptRepository(db_session))

    # When
    deleted = await service.delete_receipt(receipt.id)

    # Then
    assert deleted is True
    assert storage.deleted == [
        receipt_object_name(user.id, "photo-a"),
        receipt_object_name(user.id, "photo-b"),
    ]


@pytest.mark.asyncio
async def test_deleting_a_receipt_takes_its_line_items(db_session: AsyncSession) -> None:
    # Given
    user = await UserFactory.create_async(email="delete-items@example.com")
    current_user_id.set(user.id)
    receipt = await _receipt_with_photos(db_session, user.id, [])
    db_session.add(
        LineItem(
            id=uuid.uuid4(),
            receipt_id=receipt.id,
            name="MILKA",
            quantity=1,
            unit_price=7.49,
            total_price=7.49,
        )
    )
    await db_session.flush()

    service = ReceiptService(
        storage_port=RecordingStoragePort(), repository=ReceiptRepository(db_session)
    )

    # When
    await service.delete_receipt(receipt.id)

    # Then
    remaining = await db_session.execute(
        select(func.count()).select_from(LineItem).where(LineItem.receipt_id == receipt.id)
    )
    assert remaining.scalar_one() == 0


@pytest.mark.asyncio
async def test_another_users_receipt_is_neither_deleted_nor_acknowledged(
    db_session: AsyncSession,
) -> None:
    # Given
    owner = await UserFactory.create_async(email="owner@example.com")
    intruder = await UserFactory.create_async(email="intruder@example.com")
    receipt = await _receipt_with_photos(db_session, owner.id, ["photo-a"])

    current_user_id.set(intruder.id)
    storage = RecordingStoragePort()
    service = ReceiptService(storage_port=storage, repository=ReceiptRepository(db_session))

    # When
    deleted = await service.delete_receipt(receipt.id)

    # Then
    assert deleted is False
    assert storage.deleted == []
    current_user_id.set(owner.id)
    assert await ReceiptRepository(db_session).get(receipt.id) is not None


@pytest.mark.asyncio
async def test_an_unknown_receipt_reports_nothing_deleted(db_session: AsyncSession) -> None:
    # Given
    user = await UserFactory.create_async(email="missing@example.com")
    current_user_id.set(user.id)
    service = ReceiptService(
        storage_port=RecordingStoragePort(), repository=ReceiptRepository(db_session)
    )

    # When / Then
    assert await service.delete_receipt(uuid.uuid4()) is False


@pytest.mark.asyncio
async def test_a_photo_that_will_not_delete_does_not_keep_the_receipt(
    db_session: AsyncSession,
) -> None:
    # Given storage fails on the first of two photos
    user = await UserFactory.create_async(email="storage-down@example.com")
    current_user_id.set(user.id)
    receipt = await _receipt_with_photos(db_session, user.id, ["photo-a", "photo-b"])

    storage = RecordingStoragePort(fail_on=receipt_object_name(user.id, "photo-a"))
    service = ReceiptService(storage_port=storage, repository=ReceiptRepository(db_session))

    # When
    deleted = await service.delete_receipt(receipt.id)

    # Then the row is gone and the remaining photo was still attempted
    assert deleted is True
    assert storage.deleted == [receipt_object_name(user.id, "photo-b")]
    assert await ReceiptRepository(db_session).get(receipt.id) is None


@pytest.mark.asyncio
async def test_the_job_that_produced_the_photos_forgets_them(db_session: AsyncSession) -> None:
    # Given a stored job still naming the photos of the receipt it produced
    user = await UserFactory.create_async(email="job-payload@example.com")
    current_user_id.set(user.id)
    receipt = await _receipt_with_photos(db_session, user.id, ["photo-a"])
    job = await UploadJobFactory.create_async(
        user_id=user.id,
        status=JobStatus.STORED,
        file_ids=["photo-a"],
        result_data={"extractions": [{"merchant_name": "euro sklep"}]},
    )

    service = ReceiptService(
        storage_port=RecordingStoragePort(), repository=ReceiptRepository(db_session)
    )

    # When
    await service.delete_receipt(receipt.id)

    # Then the wizard has nothing left to render dead tiles from
    await db_session.refresh(job)
    assert job.file_ids == []
    assert job.result_data is None


@pytest.mark.asyncio
async def test_a_job_naming_other_photos_is_left_alone(db_session: AsyncSession) -> None:
    # Given
    user = await UserFactory.create_async(email="other-job@example.com")
    current_user_id.set(user.id)
    receipt = await _receipt_with_photos(db_session, user.id, ["photo-a"])
    untouched = await UploadJobFactory.create_async(
        user_id=user.id,
        status=JobStatus.STORED,
        file_ids=["photo-z"],
        result_data={"extractions": []},
    )

    service = ReceiptService(
        storage_port=RecordingStoragePort(), repository=ReceiptRepository(db_session)
    )

    # When
    await service.delete_receipt(receipt.id)

    # Then
    await db_session.refresh(untouched)
    assert untouched.file_ids == ["photo-z"]
    assert untouched.result_data == {"extractions": []}
