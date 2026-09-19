from unittest.mock import AsyncMock, patch

import pytest

from app.core.config import Settings
from app.services.storage import ObjectNotFoundError, S3StorageService


@pytest.fixture
def settings() -> Settings:
    return Settings(
        database_url="postgresql+asyncpg://test:test@localhost/test",
        anthropic_api_key="test",
        s3_bucket_name="test-bucket",
    )


@pytest.mark.asyncio
async def test_s3_storage_service_upload_file(settings: Settings) -> None:
    with patch("aiobotocore.session.get_session") as mock_get_session:
        mock_client = AsyncMock()
        mock_client_ctx = AsyncMock()
        mock_client_ctx.__aenter__.return_value = mock_client
        mock_get_session.return_value.create_client.return_value = mock_client_ctx

        async with S3StorageService(settings) as service:
            key = await service.upload_file(
                "receipts/user/uuid.jpg", b"image_data", "image/jpeg", {"owner_id": "user"}
            )

            assert key == "receipts/user/uuid.jpg"
            mock_client.put_object.assert_called_once_with(
                Bucket="test-bucket",
                Key="receipts/user/uuid.jpg",
                Body=b"image_data",
                ContentType="image/jpeg",
                ServerSideEncryption="AES256",
                Metadata={"owner_id": "user"},
            )


@pytest.mark.asyncio
async def test_s3_storage_service_get_metadata_success(settings: Settings) -> None:
    with patch("aiobotocore.session.get_session") as mock_get_session:
        mock_client = AsyncMock()
        mock_client.head_object.return_value = {"Metadata": {"owner_id": "user1"}}
        mock_client_ctx = AsyncMock()
        mock_client_ctx.__aenter__.return_value = mock_client
        mock_get_session.return_value.create_client.return_value = mock_client_ctx

        async with S3StorageService(settings) as service:
            meta = await service.get_object_metadata("receipts/user1/uuid.jpg")
            assert meta == {"owner_id": "user1"}
            mock_client.head_object.assert_called_once_with(
                Bucket="test-bucket", Key="receipts/user1/uuid.jpg"
            )


@pytest.mark.asyncio
async def test_s3_storage_service_get_metadata_not_found(settings: Settings) -> None:
    from botocore.exceptions import ClientError  # type: ignore[import-untyped]

    with patch("aiobotocore.session.get_session") as mock_get_session:
        mock_client = AsyncMock()
        mock_client.head_object.side_effect = ClientError(
            {"Error": {"Code": "404", "Message": "Not Found"}}, "HeadObject"
        )
        mock_client_ctx = AsyncMock()
        mock_client_ctx.__aenter__.return_value = mock_client
        mock_get_session.return_value.create_client.return_value = mock_client_ctx

        async with S3StorageService(settings) as service:
            with pytest.raises(ObjectNotFoundError):
                await service.get_object_metadata("receipts/user1/uuid.jpg")


@pytest.mark.asyncio
async def test_s3_storage_service_generate_presigned_url(settings: Settings) -> None:
    settings.s3_endpoint_url = "http://minio:9000"
    with patch("aiobotocore.session.get_session") as mock_get_session:
        mock_client = AsyncMock()
        mock_client.generate_presigned_url.return_value = "http://localhost:9000/test-bucket/url"
        mock_client_ctx = AsyncMock()
        mock_client_ctx.__aenter__.return_value = mock_client
        mock_get_session.return_value.create_client.return_value = mock_client_ctx

        async with S3StorageService(settings) as service:
            url = await service.generate_presigned_url("receipts/user1/uuid.jpg")
            assert url == "http://localhost:9000/test-bucket/url"

            # Verify the ephemeral client was created with localhost:9000 instead of minio:9000
            create_client_calls = mock_get_session.return_value.create_client.call_args_list
            assert (
                len(create_client_calls) == 2
            )  # One for __aenter__, one for generate_presigned_url

            last_call_kwargs = create_client_calls[1].kwargs
            assert last_call_kwargs["endpoint_url"] == "http://localhost:9000"

            mock_client.generate_presigned_url.assert_called_once_with(
                "get_object",
                Params={"Bucket": "test-bucket", "Key": "receipts/user1/uuid.jpg"},
                ExpiresIn=3600,
            )


@pytest.mark.asyncio
async def test_delete_file_removes_the_object(settings: Settings) -> None:
    with patch("aiobotocore.session.get_session") as mock_get_session:
        mock_client = AsyncMock()
        mock_client_ctx = AsyncMock()
        mock_client_ctx.__aenter__.return_value = mock_client
        mock_get_session.return_value.create_client.return_value = mock_client_ctx

        async with S3StorageService(settings) as service:
            await service.delete_file("receipts/user/uuid.jpg")

        mock_client.delete_object.assert_called_once_with(
            Bucket="test-bucket", Key="receipts/user/uuid.jpg"
        )


@pytest.mark.asyncio
async def test_deleting_an_object_that_is_already_gone_succeeds(settings: Settings) -> None:
    # Given a bucket that no longer holds the key — S3 answers 204 either way,
    # which is what lets a half-finished delete be retried (BRD A12).
    with patch("aiobotocore.session.get_session") as mock_get_session:
        mock_client = AsyncMock()
        mock_client.delete_object.return_value = {"ResponseMetadata": {"HTTPStatusCode": 204}}
        mock_client_ctx = AsyncMock()
        mock_client_ctx.__aenter__.return_value = mock_client
        mock_get_session.return_value.create_client.return_value = mock_client_ctx

        # When / Then it does not raise
        async with S3StorageService(settings) as service:
            await service.delete_file("receipts/user/never-existed.jpg")


@pytest.mark.asyncio
async def test_delete_file_outside_the_context_manager_raises(settings: Settings) -> None:
    service = S3StorageService(settings)

    with pytest.raises(RuntimeError, match="async context manager"):
        await service.delete_file("receipts/user/uuid.jpg")
