from typing import Protocol


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
