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
    with patch("aiobotocore.session.get_session") as mock_get_session:
        mock_client = AsyncMock()
        mock_client.generate_presigned_url.return_value = "https://s3.aws.com/test-bucket/url"
        mock_client_ctx = AsyncMock()
        mock_client_ctx.__aenter__.return_value = mock_client
        mock_get_session.return_value.create_client.return_value = mock_client_ctx

        async with S3StorageService(settings) as service:
            url = await service.generate_presigned_url("receipts/user1/uuid.jpg")
            assert url == "https://s3.aws.com/test-bucket/url"
            mock_client.generate_presigned_url.assert_called_once_with(
                "get_object",
                Params={"Bucket": "test-bucket", "Key": "receipts/user1/uuid.jpg"},
                ExpiresIn=3600,
            )
