"""Receipt photos in Cloud Storage behave like any StoragePort (ADR-0014)."""

from types import SimpleNamespace
from typing import Any

import pytest
from google.cloud.exceptions import NotFound

from app.adapters.gcs_storage import GcsStorageService
from app.services.storage import ObjectNotFoundError


class FakeBlob:
    def __init__(self, store: dict[str, Any], name: str) -> None:
        self.store, self.name, self.metadata = store, name, None

    def upload_from_string(self, content: bytes, content_type: str) -> None:
        self.store[self.name] = (content, content_type, self.metadata)

    def download_as_bytes(self) -> bytes:
        if self.name not in self.store:
            raise NotFound("missing")  # type: ignore[no-untyped-call]
        return bytes(self.store[self.name][0])

    def delete(self) -> None:
        if self.store.pop(self.name, None) is None:
            raise NotFound("missing")  # type: ignore[no-untyped-call]

    def generate_signed_url(self, **options: Any) -> str:
        return f"https://signed/{self.name}?v={options['version']}"


class FakeBucket:
    def __init__(self, store: dict[str, Any]) -> None:
        self.store = store

    def blob(self, name: str) -> FakeBlob:
        return FakeBlob(self.store, name)

    def get_blob(self, name: str) -> Any:
        if name not in self.store:
            return None
        return SimpleNamespace(metadata=self.store[name][2])


class FakeClient:
    def __init__(self) -> None:
        self.store: dict[str, Any] = {}

    def bucket(self, name: str) -> FakeBucket:
        assert name == "photos"
        return FakeBucket(self.store)


def _service(client: FakeClient) -> GcsStorageService:
    return GcsStorageService(SimpleNamespace(s3_bucket_name="photos"), client=client)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_a_stored_photo_comes_back_with_its_owner_metadata() -> None:
    client = FakeClient()
    async with _service(client) as photos:
        await photos.upload_file("receipts/u1/f1", b"jpeg", "image/jpeg", {"owner_id": "u1"})

        assert await photos.download_file("receipts/u1/f1") == b"jpeg"
        assert await photos.get_object_metadata("receipts/u1/f1") == {"owner_id": "u1"}
        assert (await photos.generate_presigned_url("receipts/u1/f1")).startswith("https://signed/")


@pytest.mark.asyncio
async def test_a_missing_photo_is_object_not_found_and_deleting_it_is_not_an_error() -> None:
    async with _service(FakeClient()) as photos:
        with pytest.raises(ObjectNotFoundError):
            await photos.download_file("receipts/u1/none")
        with pytest.raises(ObjectNotFoundError):
            await photos.get_object_metadata("receipts/u1/none")
        await photos.delete_file("receipts/u1/none")
