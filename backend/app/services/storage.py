from contextlib import AsyncExitStack
from typing import Any

import aiobotocore.session  # type: ignore[import-untyped]
from botocore.config import Config  # type: ignore[import-untyped]
from botocore.exceptions import ClientError  # type: ignore[import-untyped]

from app.core.config import Settings
from app.ports.storage import StoragePort


class ObjectNotFoundError(Exception):
    """Raised when an object does not exist in storage."""

    pass


class S3StorageService(StoragePort):
    """S3-compatible object storage client using aiobotocore."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.bucket = settings.s3_bucket_name
        self.region = settings.aws_region
        self.endpoint_url = settings.s3_endpoint_url
        self.access_key = (
            settings.aws_access_key_id.get_secret_value() if settings.aws_access_key_id else None
        )
        self.secret_key = (
            settings.aws_secret_access_key.get_secret_value()
            if settings.aws_secret_access_key
            else None
        )

        self._session = aiobotocore.session.get_session()
        self._exit_stack = AsyncExitStack()
        self._client: Any = None

    async def __aenter__(self) -> "S3StorageService":
        client_kwargs: dict[str, Any] = {
            "region_name": self.region,
            "endpoint_url": self.endpoint_url,
            "config": Config(signature_version="s3v4"),
        }
        if self.access_key and self.secret_key:
            client_kwargs["aws_access_key_id"] = self.access_key
            client_kwargs["aws_secret_access_key"] = self.secret_key

        client_ctx = self._session.create_client("s3", **client_kwargs)
        self._client = await self._exit_stack.enter_async_context(client_ctx)
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self._exit_stack.aclose()
        self._client = None

    async def upload_file(
        self,
        object_name: str,
        content: bytes,
        content_type: str,
        metadata: dict[str, str] | None = None,
    ) -> str:
        if not self._client:
            raise RuntimeError("S3StorageService must be used as an async context manager.")

        kwargs: dict[str, Any] = {
            "Bucket": self.bucket,
            "Key": object_name,
            "Body": content,
            "ContentType": content_type,
            "ServerSideEncryption": "AES256",
        }
        if metadata:
            kwargs["Metadata"] = metadata

        # BRD A12, N1: Encryption at rest using AWS managed keys (AES256)
        await self._client.put_object(**kwargs)
        return object_name

    async def get_object_metadata(self, object_name: str) -> dict[str, str]:
        if not self._client:
            raise RuntimeError("S3StorageService must be used as an async context manager.")

        try:
            response = await self._client.head_object(Bucket=self.bucket, Key=object_name)
            return dict(response.get("Metadata", {}))
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                raise ObjectNotFoundError(f"Object {object_name} not found") from e
            raise

    async def generate_presigned_url(self, object_name: str, expiration_seconds: int = 3600) -> str:
        if not self._client:
            raise RuntimeError("S3StorageService must be used as an async context manager.")

        url = await self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": object_name},
            ExpiresIn=expiration_seconds,
        )
        url_str = str(url)
        # Translate internal docker-compose hostname to localhost for the browser
        if "http://minio:9000" in url_str:
            url_str = url_str.replace("http://minio:9000", "http://localhost:9000")
        return url_str

    async def download_file(self, object_name: str) -> bytes:
        """Download the raw bytes of a stored object from S3."""
        if not self._client:
            raise RuntimeError("S3StorageService must be used as an async context manager.")

        try:
            response = await self._client.get_object(Bucket=self.bucket, Key=object_name)
            async with response["Body"] as stream:
                return await stream.read()  # type: ignore[no-any-return]
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                raise ObjectNotFoundError(f"Object {object_name} not found") from e
            raise
