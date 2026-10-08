"""Photo intake: the original receipt channel (BRD A1-A6, F11.1).

Stores each photo under its owner's prefix in object storage, reads it with the
vision parser, and merges the photos of one receipt into one extraction, flagging
items caught in two overlapping shots (B2-B4).
"""

import io
import logging
import uuid
from typing import Any

import pillow_heif
from PIL import Image

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

    async def ingest(self, user: User, payload: list[UploadedFile]) -> IngestionResult:
        """Store every photo of one receipt and read them as one extraction.

        Raises whatever storage raises on upload; a parser failure is not raised
        but reported as ``{"error": "extraction_failed"}`` in the extraction.
        """
        file_ids: list[str] = []
        content_types: list[str] = []
        for upload in payload:
            file_ids.append(await self.store_image(user, upload["content"], upload["content_type"]))
            content_types.append(upload["content_type"])

        extraction: dict[str, object] = {}
        if self.parser_port is not None:
            extraction = await self._run_extraction(user, file_ids, content_types)
        extraction["file_ids"] = file_ids
        return IngestionResult(extraction=extraction, file_ids=file_ids)

    async def store_image(self, user: User, content: bytes, content_type: str) -> str:
        """Uploads a receipt image to object storage, tagged with owner ID."""
        # Convert HEIC to JPEG so browsers can render it natively via presigned URLs
        if (
            content_type.lower() in ("image/heic", "image/heif")
            or content.startswith(b"\x00\x00\x00\x1cftypheic")
            or content.startswith(b"\x00\x00\x00\x18ftypheic")
        ):
            pillow_heif.register_heif_opener()  # type: ignore[attr-defined]
            try:
                img: Image.Image = Image.open(io.BytesIO(content))
                if img.mode not in ("RGB", "L"):
                    img = img.convert("RGB")
                out = io.BytesIO()
                img.save(out, format="JPEG")
                content = out.getvalue()
                content_type = "image/jpeg"
            except Exception:
                logger.exception("HEIC conversion failed for user %s", user.id)

        file_id = str(uuid.uuid4())
        object_name = receipt_object_name(user.id, file_id)
        metadata = {"owner_id": str(user.id)}

        await self.storage_port.upload_file(object_name, content, content_type, metadata)
        return file_id

    async def _run_extraction(
        self, user: User, file_ids: list[str], content_types: list[str]
    ) -> dict[str, object]:
        """Download stored images and send them to the vision parser.

        Returns the extraction result as a plain dict suitable for JSON
        storage in ``UploadJob.result_data``.
        """
        assert self.parser_port is not None

        merged_extraction: dict[str, Any] | None = None
        all_line_items: list[dict[str, Any]] = []
        parsed_headers: dict[str, dict[str, Any]] = {}

        for file_id, ct in zip(file_ids, content_types, strict=True):
            object_name = receipt_object_name(user.id, file_id)
            image_bytes = await self.storage_port.download_file(object_name)

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
