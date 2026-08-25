import filetype  # type: ignore[import-untyped]

from app.api.errors import UnsupportedFileFormatError


class ReceiptService:
    """Business logic for receipt processing and ingestion."""

    # BRD A1: Supported formats
    SUPPORTED_MIME_TYPES = frozenset(
        {
            "image/jpeg",
            "image/png",
            "image/heic",
            "application/pdf",
        }
    )

    def validate_receipt_file(self, content: bytes) -> None:
        """Validate that the file is a supported image format or PDF.

        Used to enforce BRD A1 and A2 by inspecting content rather than
        relying on the client's reported content-type or file extension.

        Raises:
            UnsupportedFileFormatError: If the format is not accepted (BRD A2).
        """
        kind = filetype.guess(content)

        if kind is None or kind.mime not in self.SUPPORTED_MIME_TYPES:
            raise UnsupportedFileFormatError(
                "Receipts come in as JPEG, PNG, HEIC or a PDF scan. "
                "The other files on this line are fine."
            )
