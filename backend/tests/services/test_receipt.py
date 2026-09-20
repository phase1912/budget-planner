import uuid
from collections.abc import Sequence
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.errors import UnsupportedFileFormatError
from app.models.category import Category
from app.models.upload_job import JobStatus, UploadJob
from app.models.user import User
from app.schemas.extraction import ExtractedLineItem
from app.services.receipt import ReceiptService


def _session_returning(job: UploadJob, categories: list[Category]) -> AsyncMock:
    """A session that answers the two queries the upload task issues.

    `process_upload_job_task` opens its own session, loads the job, then asks
    the category repository what the user may be filed under. Which statement
    is which is read off the compiled SQL because both go through `execute`.
    """
    session = AsyncMock()
    session.add = MagicMock()

    def execute(stmt: Any, *args: Any, **kwargs: Any) -> MagicMock:
        result = MagicMock()
        if "FROM categories" in str(stmt):
            result.scalars.return_value.all.return_value = categories
        else:
            result.scalar_one_or_none.return_value = job
        return result

    session.execute.side_effect = execute
    return session


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
async def test_store_receipt_image_heic_conversion() -> None:
    mock_port = AsyncMock()
    service = ReceiptService(storage_port=mock_port)
    user = User(id="test-user-id", email="test@test.com")

    # Create a valid dummy HEIC file structure so that pillow_heif doesn't throw a parsing error.
    # Actually, if we just mock Image.open and pillow_heif, we don't need a real HEIC file.
    # But since the conversion logic uses real PIL, we need to mock it or provide a real image.
    import io

    from PIL import Image

    # Generate a dummy JPEG to simulate the conversion output
    dummy_img = Image.new("RGB", (10, 10))
    dummy_io = io.BytesIO()
    dummy_img.save(dummy_io, format="JPEG")
    expected_jpeg_content = dummy_io.getvalue()

    # We will mock Image.open to return our dummy_img
    from unittest.mock import patch

    with patch("PIL.Image.open") as mock_open:
        mock_open.return_value = dummy_img
        # Pass a fake HEIC signature so it enters the conversion block
        fake_heic_bytes = b"\x00\x00\x00\x1cftypheic_fake_data"
        file_id = await service.store_receipt_image(user, fake_heic_bytes, "image/heic")

    assert "-" in file_id

    # Verify that upload_file was called with the converted JPEG content and content_type
    mock_port.upload_file.assert_called_once()
    args, _ = mock_port.upload_file.call_args
    assert args[1] == expected_jpeg_content
    assert args[2] == "image/jpeg"


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


@pytest.mark.asyncio
async def test_process_upload_job_task_position_matches() -> None:
    mock_storage = AsyncMock()
    mock_parser = AsyncMock()

    # We will upload 2 photos for 1 receipt
    # The parser will be called twice (once per photo)
    # Mock parser to return two different extractions that have a common line item

    mock_extraction_1 = MagicMock()
    mock_extraction_1.model_dump.return_value = {
        "merchant_name": "Test",
        "receipt_total": "100.00",
        "currency": "USD",
        "items_sum_matches_total": True,
        "line_items": [
            {
                "name": "Bananas",
                "unit_price": "3.20",
                "quantity": "1",
                "total_price": "3.20",
            },
            {
                "name": "Apples",
                "unit_price": "2.00",
                "quantity": "2",
                "total_price": "4.00",
            },
        ],
    }

    mock_extraction_2 = MagicMock()
    mock_extraction_2.model_dump.return_value = {
        "merchant_name": "Test",
        "receipt_total": "100.00",
        "currency": "USD",
        "items_sum_matches_total": True,
        "line_items": [
            {
                "name": "Bananas",
                "unit_price": "3.20",
                "quantity": "1",
                "total_price": "3.20",
            },
            {
                "name": "Oranges",
                "unit_price": "1.00",
                "quantity": "5",
                "total_price": "5.00",
            },
        ],
    }

    mock_parser.parse.side_effect = [mock_extraction_1, mock_extraction_2]
    mock_storage.download_file.return_value = b"image-data"

    service = ReceiptService(storage_port=mock_storage, parser_port=mock_parser)

    job_id = uuid.uuid4()
    user = User(id=uuid.uuid4(), email="test@test.com")

    # 1 receipt, 2 photos
    receipts_data: list[list[dict[str, str | bytes]]] = [
        [
            {"content": b"photo1", "content_type": "image/jpeg"},
            {"content": b"photo2", "content_type": "image/jpeg"},
        ]
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
        mock_store.side_effect = ["file-1", "file-2"]
        await service.process_upload_job_task(job_id, user, receipts_data)

    assert mock_job.status == JobStatus.COMPLETED
    assert mock_job.result_data is not None

    extractions = mock_job.result_data["extractions"]
    assert len(extractions) == 1  # 1 receipt
    extracted = extractions[0]

    assert len(extracted["line_items"]) == 4

    matches = extracted.get("position_matches", [])
    assert len(matches) == 1

    match = matches[0]
    # item_a_index should be the index of Bananas in photo 1 (0)
    # item_b_index should be the index of Bananas in photo 2 (2)
    assert match["item_a_index"] == 0
    assert match["item_b_index"] == 2
    assert match["result"] == "same"


@pytest.mark.asyncio
async def test_run_extraction_skips_matching_for_distinct_receipts() -> None:
    mock_storage = AsyncMock()
    mock_parser = AsyncMock()

    mock_storage.download_file.side_effect = [b"img1", b"img2"]

    # First image extraction
    mock_ext1 = MagicMock()
    mock_ext1.model_dump.return_value = {
        "merchant_name": "Store A",
        "transaction_date": "2026-07-01",
        "line_items": [
            {"name": "Milk 2% 1L", "total_price": "4.50", "quantity": "1", "unit_price": "4.50"}
        ],
    }

    # Second image extraction (distinct receipt)
    mock_ext2 = MagicMock()
    mock_ext2.model_dump.return_value = {
        "merchant_name": "Store B",
        "transaction_date": "2026-07-08",
        "line_items": [
            {"name": "Milk 2% 1L", "total_price": "4.50", "quantity": "1", "unit_price": "4.50"}
        ],
    }

    mock_parser.parse.side_effect = [mock_ext1, mock_ext2]

    service = ReceiptService(storage_port=mock_storage, parser_port=mock_parser)
    user = User(id=uuid.uuid4(), email="test@test.com")

    result = await service._run_extraction(user, ["f1", "f2"], ["image/jpeg", "image/png"])

    assert len(cast(list[Any], result.get("line_items", []))) == 2
    assert result.get("position_matches") == []


class _StubCategoriser:
    """A substitutable `ItemCategoriserPort`: files everything under one category.

    Honours the port's contract rather than a convenient subset of it — it
    mutates the items it is given and returns them — so a change to the real
    adapter's contract breaks this test instead of quietly passing.
    """

    def __init__(self, category: Category) -> None:
        self.category = category

    async def categorise_items(
        self, items: list[ExtractedLineItem], categories: Sequence[Category]
    ) -> list[ExtractedLineItem]:
        for item in items:
            item.category_id = self.category.id
            item.category_name = self.category.name
            item.category_confidence = 95
        return items


@pytest.mark.asyncio
async def test_extracted_items_carry_their_category_into_the_job_result() -> None:
    """The wizard reads categories off `result_data`, so they must be written there (BRD C1)."""
    category = Category(id=uuid.uuid4(), name="Groceries")

    mock_storage = AsyncMock()
    mock_parser = AsyncMock()
    mock_extraction = MagicMock()
    mock_extraction.model_dump.return_value = {
        "merchant_name": "Test",
        "receipt_total": "100.00",
        "currency": "USD",
        "items_sum_matches_total": True,
        "line_items": [
            {"name": "Milk", "quantity": "1", "unit_price": "2.0", "total_price": "2.0"}
        ],
    }
    mock_parser.parse.return_value = mock_extraction
    mock_storage.download_file.return_value = b"image-data"

    service = ReceiptService(
        storage_port=mock_storage,
        parser_port=mock_parser,
        categoriser_port=_StubCategoriser(category),
    )

    job_id = uuid.uuid4()
    user = User(id=uuid.uuid4(), email="test@test.com")
    job = UploadJob(id=job_id, user_id=user.id)
    receipts_data: list[list[dict[str, str | bytes]]] = [
        [{"content": b"test", "content_type": "image/jpeg"}]
    ]

    session = _session_returning(job=job, categories=[category])
    session_factory = MagicMock()
    session_factory.return_value.__aenter__.return_value = session

    with (
        patch("app.services.receipt.get_session_factory", return_value=session_factory),
        patch.object(service, "store_receipt_image", new_callable=AsyncMock) as mock_store,
    ):
        mock_store.return_value = "file-123"
        await service.process_upload_job_task(job_id, user, receipts_data)

    assert job.status == JobStatus.COMPLETED
    assert job.result_data is not None
    item = job.result_data["extractions"][0]["line_items"][0]
    assert item["category_id"] == str(category.id)
    assert item["category_name"] == "Groceries"
    assert item["category_confidence"] == 95


@pytest.mark.asyncio
async def test_items_stay_uncategorised_when_no_categoriser_is_wired_in() -> None:
    """Without a categoriser, confidence stays absent rather than defaulting to certainty."""
    mock_storage = AsyncMock()
    mock_parser = AsyncMock()
    mock_extraction = MagicMock()
    mock_extraction.model_dump.return_value = {
        "merchant_name": "Test",
        "receipt_total": "2.00",
        "currency": "PLN",
        "line_items": [
            {"name": "Milk", "quantity": "1", "unit_price": "2.0", "total_price": "2.0"}
        ],
    }
    mock_parser.parse.return_value = mock_extraction
    mock_storage.download_file.return_value = b"image-data"

    service = ReceiptService(storage_port=mock_storage, parser_port=mock_parser)

    job_id = uuid.uuid4()
    user = User(id=uuid.uuid4(), email="test@test.com")
    job = UploadJob(id=job_id, user_id=user.id)

    session = _session_returning(job=job, categories=[])
    session_factory = MagicMock()
    session_factory.return_value.__aenter__.return_value = session

    with (
        patch("app.services.receipt.get_session_factory", return_value=session_factory),
        patch.object(service, "store_receipt_image", new_callable=AsyncMock) as mock_store,
    ):
        mock_store.return_value = "file-123"
        await service.process_upload_job_task(
            job_id, user, [[{"content": b"test", "content_type": "image/jpeg"}]]
        )

    assert job.result_data is not None
    item = job.result_data["extractions"][0]["line_items"][0]
    assert item.get("category_id") is None
    assert item.get("category_confidence") is None
