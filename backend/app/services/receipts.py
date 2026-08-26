import uuid

import filetype  # type: ignore[import-untyped]

from app.api.errors import UnsupportedFileFormatError
from app.models.user import User
from app.ports.storage import StoragePort


class ReceiptService:
    """Business logic for receipt processing and ingestion."""

    SUPPORTED_MIME_TYPES = frozenset(
        {
            "image/jpeg",
            "image/png",
            "image/heic",
            "application/pdf",
        }
    )

    def __init__(self, storage_port: StoragePort | None = None):
        self.storage_port = storage_port

    def validate_receipt_file(self, content: bytes) -> None:
        """Validate that the file is a supported image format or PDF."""
        kind = filetype.guess(content)

        if kind is None or kind.mime not in self.SUPPORTED_MIME_TYPES:
            raise UnsupportedFileFormatError(
                "Receipts come in as JPEG, PNG, HEIC or a PDF scan. "
                "The other files on this line are fine."
            )

    async def store_receipt_image(self, user: User, content: bytes, content_type: str) -> str:
        """Uploads a receipt image to object storage, tagged with owner ID."""
        if not self.storage_port:
            raise RuntimeError("Storage port not configured.")

        file_id = str(uuid.uuid4())
        object_name = f"receipts/{user.id}/{file_id}"
        metadata = {"owner_id": str(user.id)}

        await self.storage_port.upload_file(object_name, content, content_type, metadata)
        return file_id

    async def get_presigned_url_for_image(self, user: User, file_id: str) -> str:
        """Generates a presigned URL for a receipt image, ensuring ownership."""
        if not self.storage_port:
            raise RuntimeError("Storage port not configured.")

        object_name = f"receipts/{user.id}/{file_id}"

        from app.services.storage import ObjectNotFoundError

        try:
            # We must verify the object exists before generating a URL,
            # otherwise we might generate a valid URL for a non-existent object
            await self.storage_port.get_object_metadata(object_name)
        except ObjectNotFoundError:
            raise ObjectNotFoundError(
                f"Image {file_id} not found or you don't have access to it."
            ) from None

        return await self.storage_port.generate_presigned_url(object_name)
