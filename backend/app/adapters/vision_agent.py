"""Vision adapter: turns receipt photos into structured data via the Agent.

Implements ``ReceiptParserPort`` by sending receipt images to the universal
Agent (which routes to whichever LLM provider is configured) and asking for
a JSON response matching ``ExtractedReceipt``.

This adapter is the only place in the codebase that knows what prompt to send
for receipt extraction.  The prompt is version-controlled here, and
``CURRENT_PARSER_VERSION`` (in ``app.ports.parsing``) is bumped when it
changes in a way that could alter results (BRD A15).
"""

from __future__ import annotations

from app.agent.core import Agent
from app.agent.types import ImageContent, Message
from app.schemas.extraction import ExtractedReceipt

RECEIPT_EXTRACTION_PROMPT = """\
You are a receipt parser. You will be given one or more photos of a single \
receipt (the same physical receipt may be photographed in overlapping shots).

Extract the following into the JSON schema provided:
- merchant_name: the store or restaurant name from the header
- transaction_date: in YYYY-MM-DD format
- transaction_time: in HH:MM format (24-hour)
- currency: ISO 4217 code (e.g. PLN, USD, EUR)
- line_items: every purchased item with name, quantity, unit_price, total_price
- receipt_total: the printed total from the footer
- items_sum_matches_total: true if the sum of line item totals equals the \
  receipt total, false if they differ, null if either side is missing

For each extracted field (merchant_name, transaction_date, etc.), set the corresponding
confidence score:
- 100 if clearly readable
- 50-90 if partially readable or inferred
- Below 50 if guessing
For ALL `_confidence` fields and `confidence` fields inside `line_items`:
   you MUST return an integer between 0 and 100 representing your confidence.
   DO NOT return floats.

Also, set `is_receipt_confidence` (0 to 100) indicating whether the image
actually looks like a receipt (100 = definitely a receipt, 0 = definitely not).

IMPORTANT:
1. Return ONLY valid JSON matching the schema. No extra text or explanation. Always extract
   all line items if visible.
2. For prices, extract exactly as printed.
3. If quantity or unit price is not explicitly printed for an item, infer them (e.g., quantity "1",
   unit_price same as total_price). DO NOT skip line items just because these details are implicit.
"""


class VisionAgentAdapter:
    """Extracts structured receipt data from photos using the AI agent.

    This is the concrete adapter injected by FastAPI's dependency system
    wherever ``ReceiptParserPort`` is needed.
    """

    def __init__(self, agent: Agent) -> None:
        self._agent = agent

    async def parse(
        self, images: list[bytes], *, mime_types: list[str] | None = None
    ) -> ExtractedReceipt:
        """Send receipt images to the LLM and return structured extraction.

        Builds a multi-modal message with all images and the extraction prompt,
        then asks the Agent for a ``ExtractedReceipt``-shaped JSON response.
        """
        resolved_types = mime_types or ["image/jpeg"] * len(images)

        content_parts: list[dict[str, object]] = [
            {"type": "text", "text": RECEIPT_EXTRACTION_PROMPT}
        ]
        for img_bytes, mime in zip(images, resolved_types, strict=True):
            content_parts.append(ImageContent(data=img_bytes, media_type=mime).to_content_part())

        messages = [
            Message(role="user", content=content_parts),
        ]

        return await self._agent.run_structured(messages, schema=ExtractedReceipt)
