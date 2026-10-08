"""The port every receipt intake channel implements (F11.1, BRD A12, A15).

A channel turns whatever it receives into one extraction for the rest of the
pipeline; categorisation, review and budgeting never learn which channel it was.
"""

from dataclasses import dataclass
from typing import Protocol, TypedDict, TypeVar

from app.models.receipt import ReceiptChannel
from app.models.user import User


class UploadedFile(TypedDict):
    """One photo as the upload endpoint received it."""

    content: bytes
    content_type: str


PayloadT_contra = TypeVar("PayloadT_contra", contravariant=True)


@dataclass(frozen=True)
class IngestionResult:
    """One receipt's extraction, ``ExtractedReceipt``-shaped plus ``file_ids``.

    A failed read is ``{"error": "extraction_failed"}`` rather than an exception,
    so the job can still finish and send the receipt to review.
    """

    extraction: dict[str, object]
    file_ids: list[str]


class ReceiptIngestionPort(Protocol[PayloadT_contra]):
    """One intake channel; `PayloadT_contra` is what that channel receives."""

    channel: ReceiptChannel

    async def ingest(self, user: User, payload: PayloadT_contra) -> IngestionResult:
        """Turn one receipt's raw input, owned by `user`, into an extraction."""
        ...
