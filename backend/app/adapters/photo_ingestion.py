"""Photo intake: the original receipt channel (BRD A1-A6, F11.1).

Stores each photo under its owner's prefix in object storage, reads it with the
vision parser, and merges the photos of one receipt into one extraction, flagging
items caught in two overlapping shots (B2-B4).
"""

import asyncio
import io
import logging
import uuid
from typing import Any

import pillow_heif
from PIL import Image, ImageOps

from app.domain.position_matching import (
    ComparisonNotPossible,
    MatchResult,
    are_photos_from_same_receipt,
    match_positions,
)
from app.models.receipt import ReceiptChannel
from app.models.user import User
from app.ports.ingestion import IngestionResult, UploadedFile
from app.ports.parsing import ReceiptParserPort
from app.ports.storage import StoragePort, receipt_object_name
from app.schemas.extraction import ExtractedReceipt, PositionMatch

logger = logging.getLogger(__name__)

KEPT_PHOTO_SIDE = 2000
"""Longest side, in pixels, of a photo kept after it was read (F17.9.3)."""
KEPT_PHOTO_QUALITY = 82
READ_PHOTO_SIDE = 3000
"""Longest side, in pixels, of a photo sent to be read: small print stays legible, and a
phone's 12-megapixel original no longer travels to the model at four times the size."""
READ_PHOTO_QUALITY = 90


def _is_heic(content: bytes, content_type: str) -> bool:
    return (
        content_type.lower() in ("image/heic", "image/heif")
        or content.startswith(b"\x00\x00\x00\x1cftypheic")
        or content.startswith(b"\x00\x00\x00\x18ftypheic")
    )


def prepare_photo(content: bytes, content_type: str) -> tuple[bytes, str]:
    """The photo as it is stored and read: upright, JPEG, at most 3000 px on its longest side.

    An iPhone's HEIC becomes JPEG so browsers show it; a photo turned by its EXIF tag is
    turned upright so the model reads lines, not columns. A JPEG or PNG already upright
    and small enough is left untouched. CPU-heavy — callers run it in a thread, never on
    the event loop, where a 12-megapixel decode stalled every other request for seconds.
    A PDF, or anything Pillow cannot open, comes back as it was.
    """
    if not content_type.lower().startswith("image/") and not _is_heic(content, content_type):
        return content, content_type
    pillow_heif.register_heif_opener()  # type: ignore[attr-defined]
    try:
        with Image.open(io.BytesIO(content)) as opened:
            turned = opened.getexif().get(0x0112, 1) not in (None, 1)
            too_big = max(opened.size) > READ_PHOTO_SIDE
            if not (turned or too_big or _is_heic(content, content_type)):
                return content, content_type
            image = ImageOps.exif_transpose(opened).convert("RGB")
    except Exception:
        logger.warning("A photo could not be prepared; it is read as uploaded")
        return content, content_type
    image.thumbnail((READ_PHOTO_SIDE, READ_PHOTO_SIDE))
    out = io.BytesIO()
    image.save(out, format="JPEG", quality=READ_PHOTO_QUALITY)
    return out.getvalue(), "image/jpeg"


def compress_photo(content: bytes) -> bytes | None:
    """The photo as kept after reading: JPEG, at most 2000 px on its longest side.

    Enough to see every line on screen and in a settlement, at a fraction of a phone's
    original — a 4-5 MB shot keeps about 0.4 MB. None when it is not a picture Pillow
    reads, or would not get smaller: then the original is kept.
    """
    pillow_heif.register_heif_opener()  # type: ignore[attr-defined]
    try:
        with Image.open(io.BytesIO(content)) as opened:
            image = opened.convert("RGB")
    except Exception:
        return None
    image.thumbnail((KEPT_PHOTO_SIDE, KEPT_PHOTO_SIDE))
    out = io.BytesIO()
    image.save(out, format="JPEG", quality=KEPT_PHOTO_QUALITY, optimize=True)
    smaller = out.getvalue()
    return smaller if len(smaller) < len(content) else None


class PhotoIngestionAdapter:
    """The photo channel of `ReceiptIngestionPort`: upload, then vision extraction.

    Without a parser the photos are still stored and the extraction carries only
    their file ids, so a deployment with no model configured still keeps what the
    user uploaded.
    """

    channel = ReceiptChannel.PHOTO

    def __init__(self, storage_port: StoragePort, parser_port: ReceiptParserPort | None) -> None:
        self.storage_port = storage_port
        self.parser_port = parser_port

    async def ingest(
        self, user: User, payload: list[UploadedFile], *, compress: bool = True
    ) -> IngestionResult:
        """Store every photo of one receipt and read them as one extraction.

        With `compress` False the stored photos stay as read, for a caller that may read
        them again — a recheck of a total that does not add up — and then calls
        `compress_stored`; the hardest receipts are never re-read from the smaller copy.

        Raises whatever storage raises on upload; a parser failure is not raised
        but reported as ``{"error": "extraction_failed"}`` in the extraction.
        """
        prepared: list[UploadedFile] = []
        for upload in payload:
            content, content_type = await asyncio.to_thread(
                prepare_photo, upload["content"], upload["content_type"]
            )
            prepared.append({"content": content, "content_type": content_type})
        file_ids: list[str] = []
        for photo in prepared:
            file_ids.append(await self.store_image(user, photo["content"], photo["content_type"]))
        content_types = [photo["content_type"] for photo in prepared]

        extraction: dict[str, object] = {}
        if self.parser_port is not None:
            extraction = await self._run_extraction(
                user, file_ids, content_types, contents=[p["content"] for p in prepared]
            )
        if compress:
            await self._keep_compressed(user, file_ids, prepared)
        extraction["file_ids"] = file_ids
        return IngestionResult(extraction=extraction, file_ids=file_ids)

    async def compress_stored(self, user: User, file_ids: list[str]) -> None:
        """Replace stored photos, once reading is over, with their kept versions.

        A photo that cannot be read back stays as it was: the receipt is never at risk.
        """
        for file_id in file_ids:
            name = receipt_object_name(user.id, file_id)
            try:
                content = await self.storage_port.download_file(name)
            except Exception:
                logger.warning("Photo %s kept uncompressed: could not be read back", file_id)
                continue
            await self._keep_compressed(
                user, [file_id], [{"content": content, "content_type": "image/jpeg"}]
            )

    async def _keep_compressed(
        self, user: User, file_ids: list[str], payload: list[UploadedFile]
    ) -> None:
        """Replace each stored photo, now read at full quality, with its kept version.

        A PDF, or a photo that fails to compress or to upload, stays as it was: the
        receipt is never at risk for the sake of space.
        """
        for file_id, upload in zip(file_ids, payload, strict=True):
            if not upload["content_type"].lower().startswith("image/"):
                continue
            smaller = await asyncio.to_thread(compress_photo, upload["content"])
            if smaller is None:
                continue
            try:
                await self.storage_port.upload_file(
                    receipt_object_name(user.id, file_id),
                    smaller,
                    "image/jpeg",
                    {"owner_id": str(user.id)},
                )
            except Exception:
                logger.warning("Photo %s kept uncompressed: upload failed", file_id)

    async def store_image(self, user: User, content: bytes, content_type: str) -> str:
        """Uploads a receipt image to object storage, tagged with owner ID."""
        # HEIC becomes JPEG so browsers can show it; off the event loop (see prepare_photo).
        if _is_heic(content, content_type):
            content, content_type = await asyncio.to_thread(prepare_photo, content, content_type)

        file_id = str(uuid.uuid4())
        object_name = receipt_object_name(user.id, file_id)
        metadata = {"owner_id": str(user.id)}

        await self.storage_port.upload_file(object_name, content, content_type, metadata)
        return file_id

    async def _run_extraction(
        self,
        user: User,
        file_ids: list[str],
        content_types: list[str],
        *,
        contents: list[bytes] | None = None,
    ) -> dict[str, object]:
        """Send the photos to the vision parser, from `contents` when the caller still
        holds them, else downloaded from storage.

        Returns the extraction result as a plain dict suitable for JSON
        storage in ``UploadJob.result_data``.
        """
        assert self.parser_port is not None

        merged_extraction: dict[str, Any] | None = None
        all_line_items: list[dict[str, Any]] = []
        parsed_headers: dict[str, dict[str, Any]] = {}

        for index, (file_id, ct) in enumerate(zip(file_ids, content_types, strict=True)):
            if contents is not None:
                image_bytes = contents[index]
            else:
                image_bytes = await self.storage_port.download_file(
                    receipt_object_name(user.id, file_id)
                )

            try:
                result = await self.parser_port.parse([image_bytes], mime_types=[ct])
                result_dict = result.model_dump()
                parsed_headers[file_id] = result_dict

                for item in result_dict.get("line_items", []):
                    item["file_id"] = file_id
                    all_line_items.append(item)

                if merged_extraction is None:
                    merged_extraction = result_dict
                else:
                    for field in [
                        "merchant_name",
                        "transaction_date",
                        "transaction_time",
                        "receipt_total",
                    ]:
                        conf_field = f"{field}_confidence"
                        if result_dict.get(conf_field, 0) > merged_extraction.get(conf_field, 0):
                            merged_extraction[field] = result_dict.get(field)
                            merged_extraction[conf_field] = result_dict.get(conf_field)
            except Exception:
                logger.exception(
                    "Vision extraction failed for user %s, file_id %s", user.id, file_id
                )
                return {"error": "extraction_failed"}

        if merged_extraction is None:
            return {"error": "extraction_failed"}

        merged_extraction["line_items"] = all_line_items

        try:
            final_result = ExtractedReceipt(**merged_extraction)

            matches = []
            items = final_result.line_items
            for i, a in enumerate(items):
                for j in range(i + 1, len(items)):
                    b = items[j]

                    if a.file_id and b.file_id and a.file_id != b.file_id and a.name == b.name:
                        header_a = parsed_headers.get(a.file_id, {})
                        header_b = parsed_headers.get(b.file_id, {})

                        if not are_photos_from_same_receipt(header_a, header_b):
                            continue

                        try:
                            res = match_positions(a, b, same_receipt=True)
                            matches.append(
                                PositionMatch(item_a_index=i, item_b_index=j, result=res)
                            )
                        except ComparisonNotPossible as e:
                            matches.append(
                                PositionMatch(
                                    item_a_index=i,
                                    item_b_index=j,
                                    result=MatchResult.NOT_POSSIBLE,
                                    reason=str(e),
                                )
                            )

            final_result.position_matches = matches

            return final_result.model_dump()
        except Exception:
            logger.exception("Merged extraction validation failed for user %s", user.id)
            return {"error": "extraction_failed"}
