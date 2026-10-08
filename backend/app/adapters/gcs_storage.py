"""Receipt photos in Google Cloud Storage, as the runtime's service account (ADR-0014).

Production's organisation forbids service account keys, HMAC keys included, so the S3
interoperability API is out: this talks to Cloud Storage natively with the identity
Cloud Run gives the backend. Presigned URLs are signed by IAM (`signBlob`) instead of a
private key, which needs the service account to hold Token Creator on itself.
"""

import asyncio
from datetime import timedelta
from typing import Any

import google.auth
from google.auth.credentials import Signing
from google.auth.transport.requests import Request
from google.cloud import storage  # type: ignore[attr-defined]
from google.cloud.exceptions import NotFound

from app.core.config import Settings
from app.ports.storage import StoragePort
from app.services.storage import ObjectNotFoundError


class GcsStorageService(StoragePort):
    """`StoragePort` on Cloud Storage. The client is synchronous, so calls run in threads.

    Objects are encrypted at rest by Cloud Storage itself (BRD A12, N1).
    """

    def __init__(self, settings: Settings, client: Any = None) -> None:
        self._client = client
        self._bucket_name = settings.s3_bucket_name
        self._credentials: Any = None

    async def __aenter__(self) -> "GcsStorageService":
        if self._client is None:
            self._credentials, project = google.auth.default()
            self._client = storage.Client(project=project, credentials=self._credentials)
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        return None

    def _blob(self, object_name: str) -> Any:
        return self._client.bucket(self._bucket_name).blob(object_name)

    async def upload_file(
        self,
        object_name: str,
        content: bytes,
        content_type: str,
        metadata: dict[str, str] | None = None,
    ) -> str:
        blob = self._blob(object_name)
        blob.metadata = metadata or None
        await asyncio.to_thread(blob.upload_from_string, content, content_type=content_type)
        return object_name

    async def get_object_metadata(self, object_name: str) -> dict[str, str]:
        bucket = self._client.bucket(self._bucket_name)
        blob = await asyncio.to_thread(bucket.get_blob, object_name)
        if blob is None:
            raise ObjectNotFoundError(f"Object {object_name} not found")
        return dict(blob.metadata or {})

    async def generate_presigned_url(self, object_name: str, expiration_seconds: int = 3600) -> str:
        return await asyncio.to_thread(self._sign, object_name, expiration_seconds)

    def _sign(self, object_name: str, expiration_seconds: int) -> str:
        options: dict[str, Any] = {}
        credentials = self._credentials
        if credentials is not None and not isinstance(credentials, Signing):
            # Metadata-server credentials hold no private key: refresh for a token and
            # let IAM sign with the service account's Google-held key.
            credentials.refresh(Request())
            options = {
                "service_account_email": credentials.service_account_email,
                "access_token": credentials.token,
            }
        url = self._blob(object_name).generate_signed_url(
            version="v4",
            expiration=timedelta(seconds=expiration_seconds),
            method="GET",
            **options,
        )
        return str(url)

    async def download_file(self, object_name: str) -> bytes:
        try:
            data = await asyncio.to_thread(self._blob(object_name).download_as_bytes)
        except NotFound as error:
            raise ObjectNotFoundError(f"Object {object_name} not found") from error
        return bytes(data)

    async def delete_file(self, object_name: str) -> None:
        try:
            await asyncio.to_thread(self._blob(object_name).delete)
        except NotFound:
            return
