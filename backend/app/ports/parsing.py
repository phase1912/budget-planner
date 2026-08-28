"""Ports for receipt parsing (BRD A9, A15).

``CURRENT_PARSER_VERSION`` is bumped whenever parsing logic changes in a way
that could alter extraction results — every stored receipt records this version
so a later change doesn't retroactively look like it applies to receipts parsed
under the old behaviour.

``ReceiptParserPort`` is the protocol that receipt-parsing adapters implement.
The service layer depends on this protocol, never on a concrete LLM client
(DIP from AGENTS.md).
"""

from __future__ import annotations

from typing import Protocol

from app.schemas.extraction import ExtractedReceipt

CURRENT_PARSER_VERSION = "1"


class ReceiptParserPort(Protocol):
    """Parse receipt images into structured data.

    Implementations may call an LLM (the ``VisionAgentAdapter``), read from a
    fixture (test stubs), or apply OCR — the service layer doesn't know and
    doesn't care.
    """

    async def parse(
        self, images: list[bytes], *, mime_types: list[str] | None = None
    ) -> ExtractedReceipt:
        """Extract merchant, date, line items and total from receipt photos.

        Args:
            images: Raw bytes of each receipt photo (one receipt, possibly
                photographed in multiple overlapping shots).
            mime_types: MIME type of each image, parallel to ``images``.
                Defaults to ``image/jpeg`` when not provided.

        Returns:
            A validated ``ExtractedReceipt`` with confidence scores per field.

        Raises:
            ``AgentError`` (or a subclass) when the LLM call fails entirely.
            A low-confidence or missing field is **not** an error — it is
            expressed in the schema's confidence fields and ``None`` values.
        """
        ...
