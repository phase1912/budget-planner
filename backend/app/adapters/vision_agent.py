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

import base64
from decimal import Decimal

from app.agent.core import Agent
from app.agent.types import ImageContent, Message
from app.schemas.extraction import ExtractedReceipt

EXTRACTION_MAX_TOKENS = 8192
"""Room for a long receipt several times over (one runs to about 1,500 tokens).

A small local model at temperature 0 can fall into repeating one line over and over
until it hits its limit; this bounds that to minutes instead of the default 32k.
"""

RECEIPT_EXTRACTION_PROMPT = """\
You are a receipt parser. You will be given one or more photos of a single \
receipt (the same physical receipt may be photographed in overlapping shots).

Extract the following into the JSON schema provided:
- merchant_name: the store or restaurant name from the header
- transaction_date: in YYYY-MM-DD format
- transaction_time: in HH:MM format (24-hour)
- currency: ISO 4217 code of the currency the amounts are in (e.g. PLN, UAH, USD, \
  EUR), from the code or symbol printed (zł, грн, $, €) or the country of the \
  shop's address; null if the receipt gives no way to tell
- line_items: every purchased item with name, quantity, unit_price, total_price
- receipt_total: the amount actually paid. When the footer prints both a goods \
  subtotal ("SUMA PLN") and an amount to pay ("DO ZAPŁATY", "RAZEM DO ZAPŁATY", \
  "Total due"), take the amount to pay
- fiscal_register_id, fiscal_receipt_number: the fiscal numbers that identify this \
  receipt, exactly as printed — in Poland the register number beside the fiscal logo \
  (e.g. "ECA 2201079960") and the printout number of the PARAGON FISKALNY (e.g. \
  "nr:85503"), in Ukraine the ФН of the register and the receipt's fiscal number. Use \
  the fiscal receipt's numbers, never those of a non-fiscal printout (NIEFISKALNY) on \
  the same paper. Null when the receipt prints none
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
2. For prices, give the number only. Receipts print a VAT class letter next to
   each amount ("7,49A", "13,99C") and a unit next to each quantity ("10szt") —
   leave those out and keep the decimal separator as printed ("7,49", "10").
   If a line has no price printed at all, return an empty string for it rather
   than repeating the VAT letter.
3. If quantity or unit price is not explicitly printed for an item, infer them (e.g., quantity "1",
   unit_price same as total_price). DO NOT skip line items just because these details are implicit.
4. Discount lines ("OPUST", "Rabat", "Upust") are line items of their own with a NEGATIVE
   total_price, exactly as printed under the product they reduce.
5. Returnable-packaging deposits ("kaucja", "OPAKOWANIA ZWROTNE", e.g. "But Plastik kaucja
   6 x 0,50 = 3,00") are line items too, with a positive total; a deposit handed back
   ("zwrot kaucji") is a line with a negative total. Together with the products they make
   up the amount to pay. List each deposit once: a section heading ("OPAKOWANIA ZWROTNE
   WYDANIA") or a section sum ("OPAKOWANIA ZWROTNE SUMA") is not a line of its own.
   Likewise "SUMA PLN", "PTU" and "DO ZAPŁATY" are totals, never line items.
6. NEVER invent an amount you cannot read. If a price is unreadable, cut off or hidden, return an
   empty string for it. "0" means the receipt actually printed a zero, and nothing else. Guessing
   zero silently understates what the user spent, which is worse than admitting the line is
   unreadable.
"""


RECHECK_PROMPT = """\
You read this receipt before, and the line items you found do not add up to its total.

Your previous reading (JSON):
{reading}

The lines sum to {lines_sum}; the amount to pay you read is {printed_total}; the \
difference is {gap}.

Look at the photos again, line by line, and find what was misread. Common causes:
- a discount line ("OPUST", "Rabat") missed, or read without its minus sign;
- a line read twice, or one skipped where the photos overlap;
- a misread digit in a price, or a total that is not quantity x unit price;
- a deposit ("kaucja", "OPAKOWANIA ZWROTNE") missing from the lines, or the goods \
  subtotal ("SUMA PLN") taken instead of the amount to pay ("DO ZAPŁATY").

Do not change the amount to pay unless you misread it; fix the lines. Return the \
complete corrected reading in the same JSON schema, following the same rules as before:

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
        return await self._read(RECEIPT_EXTRACTION_PROMPT, images, mime_types)

    async def recheck(
        self,
        images: list[bytes],
        *,
        mime_types: list[str],
        reading: ExtractedReceipt,
    ) -> ExtractedReceipt:
        """Read the receipt again, told what the first reading got and how far off it is (A9).

        Implements ``ReceiptRecheckerPort``. The full extraction rules are repeated, so
        the answer is a complete reading in the same shape, not a patch.
        """
        lines_sum = Decimal(reading.computed_total or "0")
        printed = Decimal((reading.receipt_total or "0").replace(",", "."))
        prompt = RECHECK_PROMPT.format(
            reading=reading.model_dump_json(
                include={"merchant_name", "line_items", "receipt_total"}, indent=1
            ),
            lines_sum=f"{lines_sum:.2f}",
            printed_total=f"{printed:.2f}",
            gap=f"{lines_sum - printed:+.2f}",
        )
        return await self._read(prompt + RECEIPT_EXTRACTION_PROMPT, images, mime_types)

    async def _read(
        self, prompt: str, images: list[bytes], mime_types: list[str] | None
    ) -> ExtractedReceipt:
        resolved_types = mime_types or ["image/jpeg"] * len(images)

        import io

        import pillow_heif
        from PIL import Image

        # Register HEIF opener with Pillow
        pillow_heif.register_heif_opener()  # type: ignore[attr-defined]

        processed_images = []
        processed_types = []

        for img_bytes, mime in zip(images, resolved_types, strict=True):
            if (
                mime.lower() in ("image/heic", "image/heif")
                or img_bytes.startswith(b"\x00\x00\x00\x1cftypheic")
                or img_bytes.startswith(b"\x00\x00\x00\x18ftypheic")
            ):
                # Convert HEIC to JPEG
                try:
                    img: Image.Image = Image.open(io.BytesIO(img_bytes))
                    if img.mode not in ("RGB", "L"):
                        img = img.convert("RGB")
                    out = io.BytesIO()
                    img.save(out, format="JPEG")
                    processed_images.append(out.getvalue())
                    processed_types.append("image/jpeg")
                except Exception as e:
                    import logging

                    logging.error(f"HEIC conversion failed: {e}")

                    # Fallback to original if conversion fails
                    processed_images.append(img_bytes)
                    processed_types.append(mime)
            else:
                processed_images.append(img_bytes)
                processed_types.append(mime)

        content_parts: list[dict[str, object]] = [{"type": "text", "text": prompt}]
        for img_bytes, mime in zip(processed_images, processed_types, strict=True):
            content_parts.append(_content_part(img_bytes, mime))

        messages = [
            Message(role="user", content=content_parts),
        ]

        return await self._agent.run_structured(
            messages, schema=ExtractedReceipt, max_tokens=EXTRACTION_MAX_TOKENS
        )


def _content_part(data: bytes, mime: str) -> dict[str, object]:
    """One input of the extraction request: an image, a PDF, or a receipt's text.

    Text and PDF come from emailed receipts (F11.2). A PDF goes in LiteLLM's
    provider-neutral `file` part, which models that read documents accept and
    others refuse with an error the caller already treats as a failed read.
    """
    if mime == "text/plain":
        return {"type": "text", "text": data.decode("utf-8", errors="replace")}
    if mime == "application/pdf":
        encoded = base64.b64encode(data).decode("ascii")
        return {"type": "file", "file": {"file_data": f"data:{mime};base64,{encoded}"}}
    return ImageContent(data=data, media_type=mime).to_content_part()
