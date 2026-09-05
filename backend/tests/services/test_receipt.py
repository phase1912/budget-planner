import uuid
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.errors import UnsupportedFileFormatError
from app.models.upload_job import JobStatus, UploadJob
from app.models.user import User
from app.services.receipt import ReceiptService


def test_validate_receipt_file_accepts_valid_formats() -> None:
    service = ReceiptService()

    # Valid JPEG magic numbers
    jpeg_content = b"\xff\xd8\xff\xe0\x00\x10\x4a\x46\x49\x46\x00\x01"
    # Valid PNG magic numbers
    png_content = b"\x89\x50\x4e\x47\x0d\x0a\x1a\x0a"
    # Valid PDF magic numbers
    pdf_content = b"%PDF-1.4\n%"

    # These should not raise
    service.validate_receipt_file(jpeg_content)
    service.validate_receipt_file(png_content)
    service.validate_receipt_file(pdf_content)


def test_validate_receipt_file_rejects_invalid_formats() -> None:
    service = ReceiptService()

    # Plain text file content
    txt_content = b"This is just some plain text, not a photo."

    with pytest.raises(UnsupportedFileFormatError) as exc_info:
        service.validate_receipt_file(txt_content)

    assert "Receipts come in as JPEG, PNG, HEIC or a PDF scan" in str(exc_info.value)


@pytest.mark.asyncio
async def test_store_receipt_image() -> None:
    mock_port = AsyncMock()
    mock_port.upload_file.return_value = "receipts/test-user-id/test-file-id"
    service = ReceiptService(storage_port=mock_port)

    user = User(id="test-user-id", email="test@test.com")
    file_id = await service.store_receipt_image(user, b"content", "image/jpeg")

    assert "-" in file_id
    assert not file_id.startswith("receipts/")
    mock_port.upload_file.assert_called_once()


@pytest.mark.asyncio
async def test_get_presigned_url_for_image_success() -> None:
    mock_port = AsyncMock()
    mock_port.get_object_metadata.return_value = {"owner_id": "test-user-id"}
    mock_port.generate_presigned_url.return_value = "https://mock-url"
    service = ReceiptService(storage_port=mock_port)

    user = User(id="test-user-id", email="test@test.com")
    url = await service.get_presigned_url_for_image(user, "test-file-id")

    assert url == "https://mock-url"
    mock_port.get_object_metadata.assert_called_once_with("receipts/test-user-id/test-file-id")
    mock_port.generate_presigned_url.assert_called_once_with("receipts/test-user-id/test-file-id")


@pytest.mark.asyncio
async def test_get_presigned_url_for_image_not_found() -> None:
    from app.services.storage import ObjectNotFoundError

    mock_port = AsyncMock()
    mock_port.get_object_metadata.side_effect = ObjectNotFoundError()
    service = ReceiptService(storage_port=mock_port)

    user = User(id="test-user-id", email="test@test.com")
    with pytest.raises(ObjectNotFoundError):
        await service.get_presigned_url_for_image(user, "test-file-id")


@pytest.mark.asyncio
async def test_process_upload_job_task_success() -> None:
    mock_storage = AsyncMock()
    mock_parser = AsyncMock()

    # Mock parser return value
    mock_extraction = MagicMock()
    mock_extraction.model_dump.return_value = {
        "merchant_name": "Test",
        "receipt_total": "100.00",
        "currency": "USD",
        "items_sum_matches_total": True,
        "line_items": [],
    }
    mock_parser.parse.return_value = mock_extraction
    mock_storage.download_file.return_value = b"image-data"

    service = ReceiptService(storage_port=mock_storage, parser_port=mock_parser)

    job_id = uuid.uuid4()
    user = User(id=uuid.uuid4(), email="test@test.com")
    receipts_data: list[list[dict[str, str | bytes]]] = [
        [{"content": b"test", "content_type": "image/jpeg"}]
    ]

    mock_job = UploadJob(id=job_id, user_id=user.id)

    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_job
    mock_session.execute.return_value = mock_result

    mock_session_factory = MagicMock()
    mock_session_factory.return_value.__aenter__.return_value = mock_session

    with (
        patch("app.services.receipt.get_session_factory", return_value=mock_session_factory),
        patch.object(service, "store_receipt_image", new_callable=AsyncMock) as mock_store,
    ):
        mock_store.return_value = "file-123"
        await service.process_upload_job_task(job_id, user, receipts_data)

    assert mock_job.status == JobStatus.COMPLETED
    assert mock_job.result_data is not None
    assert "extractions" in mock_job.result_data


@pytest.mark.asyncio
async def test_process_upload_job_task_failure() -> None:
    service = ReceiptService()

    job_id = uuid.uuid4()
    user = User(id=uuid.uuid4(), email="test@test.com")
    receipts_data: list[list[dict[str, str | bytes]]] = [
        [{"content": b"test", "content_type": "image/jpeg"}]
    ]

    mock_job = UploadJob(id=job_id, user_id=user.id, status=JobStatus.PENDING)

    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_job
    mock_session.execute.return_value = mock_result

    mock_session_factory = MagicMock()
    mock_session_factory.return_value.__aenter__.return_value = mock_session

    with (
        patch("app.services.receipt.get_session_factory", return_value=mock_session_factory),
        patch.object(service, "store_receipt_image", new_callable=AsyncMock) as mock_store,
        pytest.raises(Exception, match="Failed"),
    ):
        mock_store.side_effect = Exception("Failed")
        await service.process_upload_job_task(job_id, user, receipts_data)

    assert mock_job.status == JobStatus.FAILED


@pytest.mark.asyncio
async def test_run_extraction_multiple_photos_merges_items_and_headers() -> None:
    mock_storage = AsyncMock()
    mock_parser = AsyncMock()

    mock_storage.download_file.side_effect = [b"img1", b"img2"]

    # First image extraction
    mock_ext1 = MagicMock()
    mock_ext1.model_dump.return_value = {
        "merchant_name": "Store",
        "merchant_name_confidence": 90,
        "receipt_total": "100.00",
        "receipt_total_confidence": 50,
        "line_items": [
            {"name": "Item A", "total_price": "50.00", "quantity": "1", "unit_price": "50.00"}
        ],
    }

    # Second image extraction
    mock_ext2 = MagicMock()
    mock_ext2.model_dump.return_value = {
        "merchant_name": "Store",
        "merchant_name_confidence": 80,  # lower conf
        "receipt_total": "100.00",
        "receipt_total_confidence": 95,  # higher conf
        "line_items": [
            {"name": "Item B", "total_price": "50.00", "quantity": "1", "unit_price": "50.00"}
        ],
    }

    mock_parser.parse.side_effect = [mock_ext1, mock_ext2]

    service = ReceiptService(storage_port=mock_storage, parser_port=mock_parser)
    user = User(id=uuid.uuid4(), email="test@test.com")

    # Using private method directly for the unit test
    result = await service._run_extraction(user, ["f1", "f2"], ["image/jpeg", "image/png"])

    assert "error" not in result
    assert result["merchant_name"] == "Store"
    assert result["merchant_name_confidence"] == 90  # kept from ext1
    assert result["receipt_total"] == "100.00"
    assert result["receipt_total_confidence"] == 95  # updated from ext2

    # Line items should be combined and tagged
    items = cast(list[dict[str, Any]], result["line_items"])
    assert len(items) == 2
    assert items[0]["name"] == "Item A"
    assert items[0]["file_id"] == "f1"
    assert items[1]["name"] == "Item B"
    assert items[1]["file_id"] == "f2"


@pytest.mark.asyncio
async def test_run_extraction_failure_returns_error_dict() -> None:
    mock_storage = AsyncMock()
    mock_parser = AsyncMock()

    mock_storage.download_file.return_value = b"img1"
    mock_parser.parse.side_effect = Exception("Vision LLM Error")

    service = ReceiptService(storage_port=mock_storage, parser_port=mock_parser)
    user = User(id=uuid.uuid4(), email="test@test.com")

    result = await service._run_extraction(user, ["f1"], ["image/jpeg"])

    assert result == {"error": "extraction_failed"}
