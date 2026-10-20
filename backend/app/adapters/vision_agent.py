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
import logging
from decimal import Decimal

from app.agent.core import Agent
from app.agent.types import ImageContent, Message
from app.domain.receipt_conventions import prompt_notes
from app.schemas.extraction import ExtractedReceipt

EXTRACTION_MAX_TOKENS = 8192
"""Room for a long receipt several times over (one runs to about 1,500 tokens).

A small local model at temperature 0 can fall into repeating one line over and over
until it hits its limit; this bounds that to minutes instead of the default 32k.
"""

READING_THINKING_BUDGET = 2048
"""Tokens the model may think before it answers (F15.5): enough to check that the lines add
up and to place a wrapped name or a menu's parts, on top of the answer's own limit."""

RECEIPT_EXTRACTION_PROMPT_HEAD = """\
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
- expense_kind: what the receipt as a whole paid for, from the shop and its lines — \
  "transport" (fuel station, train or bus ticket, airline, taxi, parking, tolls, car \
  hire), "accommodation" (hotel, hostel, guesthouse, apartment rental), "meals" \
  (restaurant, café, bar, or a shop selling mostly food and drink) or "other" \
  (souvenirs, clothes, pharmacy, anything else)
- receipt_total: the receipt's total to pay, as the reading rules below define it
- fiscal_register_id, fiscal_receipt_number: the fiscal numbers that identify this \
  receipt, exactly as printed — the register's number and the receipt's own number, \
  e.g. in Poland "ECA 2201079960" beside the fiscal logo and "nr:85503" of the PARAGON \
  FISKALNY, in Ukraine the ФН of the register and the receipt's fiscal number. Use the \
  fiscal receipt's numbers, never those of a non-fiscal printout (NIEFISKALNY) on the \
  same paper. Null when the receipt prints none
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
actually looks like a receipt (100 = definitely a receipt, 0 = definitely not), and
`document_kind`: "receipt" for a purchase the user paid for; "income" when the document
shows money paid TO the user — a payslip ("pasek wynagrodzeń", "розрахунковий лист"),
a transfer they received, a refund confirmation; "other" for anything else.

IMPORTANT:
1. Return ONLY valid JSON matching the schema. No extra text or explanation. Always extract
   all line items if visible.
2. For prices, give the number only, without VAT marks or units ("7,49A" is "7,49",
   "10szt" is "10"), keeping the decimal separator as printed. If a line has no price
   printed at all, return an empty string for it rather than repeating the VAT mark.
3. If quantity or unit price is not explicitly printed for an item, infer them (e.g., quantity "1",
   unit_price same as total_price). DO NOT skip line items just because these details are implicit.
4. NEVER invent an amount you cannot read. If a price is unreadable, cut off or hidden, return an
   empty string for it. "0" means the receipt actually printed a zero, and nothing else. Guessing
   zero silently understates what the user spent, which is worse than admitting the line is
   unreadable.
5. Before answering, check that the line totals add up to receipt_total; if they do not,
   look again for a missed discount, deposit or rounding line, a menu part read as an
   item, or a footer sum read as one.

Reading rules:
"""
RECEIPT_EXTRACTION_PROMPT = RECEIPT_EXTRACTION_PROMPT_HEAD + prompt_notes()


RECHECK_PROMPT = """\
You read this receipt before, and the line items you found do not add up to its total.

Your previous reading (JSON):
{reading}

The lines sum to {lines_sum}; the amount to pay you read is {printed_total}; the \
difference is {gap}.

Look at the photos again, line by line, and find what was misread. Common causes:
- a discount line missed, or read without its minus sign;
- a footer sum of the discounts listed as a line, counting them twice;
- a rounding line missed;
- a menu's unpriced part listed as an item, or a priced add-on folded into the menu;
- a line read twice, or one skipped where the photos overlap;
- a misread digit in a price, or a total that is not quantity x unit price;
- a deposit missing from the lines, or the goods subtotal taken instead of the \
  amount to pay.

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
        readable = [
            legible(*readable_input(data, mime))
            for data, mime in zip(images, resolved_types, strict=True)
        ]
        processed_images = [data for data, _ in readable]
        processed_types = [mime for _, mime in readable]

        content_parts: list[dict[str, object]] = [{"type": "text", "text": prompt}]
        for img_bytes, mime in zip(processed_images, processed_types, strict=True):
            content_parts.append(content_part(img_bytes, mime))

        messages = [
            Message(role="user", content=content_parts),
        ]

        return await self._agent.run_structured(
            messages,
            schema=ExtractedReceipt,
            max_tokens=EXTRACTION_MAX_TOKENS,
            thinking_budget=READING_THINKING_BUDGET,
        )


def readable_input(data: bytes, mime: str) -> tuple[bytes, str]:
    """A photo the model can read: HEIC (an iPhone's default) becomes JPEG, the rest
    passes through. A conversion that fails sends the original, which the model may
    still read or refuse like any unreadable photo."""
    if not (
        mime.lower() in ("image/heic", "image/heif")
        or data.startswith(b"\x00\x00\x00\x1cftypheic")
        or data.startswith(b"\x00\x00\x00\x18ftypheic")
    ):
        return data, mime
    import io

    import pillow_heif
    from PIL import Image

    pillow_heif.register_heif_opener()  # type: ignore[attr-defined]
    try:
        img: Image.Image = Image.open(io.BytesIO(data))
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        out = io.BytesIO()
        img.save(out, format="JPEG")
        return out.getvalue(), "image/jpeg"
    except Exception:
        logging.getLogger(__name__).exception("HEIC conversion failed")
        return data, mime


PHOTO_TYPES = ("image/jpeg", "image/png", "image/webp")
LEGIBLE_SIDE = 3072
"""The longest side a photo is sent at: a long receipt keeps its small print, and a 48 MP
original does not cost four times the tokens for nothing more to read."""
MARGIN_THRESHOLD = 40
"""How far from the background colour a pixel must be to count as receipt, not table."""


def legible(data: bytes, mime: str) -> tuple[bytes, str]:
    """A photo made easier to read (F15.5): turned upright from its EXIF orientation —
    phones store a sideways photo and only note the turn — cropped to what differs from
    its background, grey, with its contrast stretched for faded thermal paper, and no
    larger than LEGIBLE_SIDE. PDFs and text pass through; a photo that cannot be processed
    is sent as it was."""
    if mime not in PHOTO_TYPES:
        return data, mime
    import io

    from PIL import Image, ImageChops, ImageOps

    try:
        image = ImageOps.exif_transpose(Image.open(io.BytesIO(data)))
        grey = ImageOps.grayscale(image)
        background = Image.new("L", grey.size, grey.getpixel((0, 0)))
        differs = ImageChops.difference(grey, background).point(
            lambda v: 255 if v > MARGIN_THRESHOLD else 0
        )
        box = differs.getbbox()
        if box:
            grey = grey.crop(box)
        grey = ImageOps.autocontrast(grey, cutoff=1)
        grey.thumbnail((LEGIBLE_SIDE, LEGIBLE_SIDE))
        out = io.BytesIO()
        grey.save(out, format="JPEG", quality=92)
        return out.getvalue(), "image/jpeg"
    except Exception:
        logging.getLogger(__name__).exception("Preparing a photo for reading failed")
        return data, mime


def content_part(data: bytes, mime: str) -> dict[str, object]:
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
