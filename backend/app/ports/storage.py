import uuid
from typing import Protocol


def receipt_object_name(user_id: uuid.UUID, file_id: str) -> str:
    """Build the object-storage key for one receipt image.

    The owning user's id is part of the key, which is what makes cross-user
    access impossible to express: a caller can only ever name keys under its
    own prefix (BRD N2).
    """
    return f"receipts/{user_id}/{file_id}"


class StoragePort(Protocol):
    """Port for object storage operations (e.g., S3)."""

    async def upload_file(
        self,
        object_name: str,
        content: bytes,
        content_type: str,
        metadata: dict[str, str] | None = None,
    ) -> str:
        """Upload a file and return its object name or key.

        The implementation must ensure encryption at rest (BRD A12, N1).
        """
        ...

    async def get_object_metadata(self, object_name: str) -> dict[str, str]:
        """Retrieve the custom metadata for an object."""
        ...

    async def generate_presigned_url(self, object_name: str, expiration_seconds: int = 3600) -> str:
        """Generate a time-limited URL for retrieving an object."""
        ...

    async def download_file(self, object_name: str) -> bytes:
        """Download and return the raw bytes of a stored object."""
        ...

    async def delete_file(self, object_name: str) -> None:
        """Permanently remove a stored object.

        Succeeds whether or not the object is there. A caller deleting a
        receipt's photos has already committed to losing them, and failing on
        one that is already gone would leave the caller unable to retry.
        """
        ...
