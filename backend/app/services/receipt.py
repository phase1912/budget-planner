import asyncio
import copy
import io
import logging
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, cast

import filetype  # type: ignore[import-untyped]
import pillow_heif
from PIL import Image
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm.attributes import flag_modified

from app.core.config import get_settings
from app.db.session import get_session_factory
from app.domain.categories import UNCATEGORIZED, confident_category
from app.models.category import Category
from app.models.line_item import LineItem
from app.models.match_override import PositionMatchOverride
from app.models.receipt import Receipt
from app.models.upload_job import JobStatus, UploadJob
from app.models.user import User
from app.ports.categorisation import ItemCategoriserPort
from app.ports.parsing import ReceiptParserPort
from app.ports.storage import StoragePort
from app.repository.category import CategoryRepository
from app.repository.receipt import ReceiptRepository
from app.schemas.extraction import ExtractedLineItem, ExtractedReceipt
from app.schemas.receipt import (
    EditLineItemRequest,
    ResolvePositionMatchRequest,
    UpdateReceiptRequest,
    UploadJobStatusResponse,
)

logger = logging.getLogger(__name__)


def receipt_object_name(user_id: uuid.UUID, file_id: str) -> str:
    """Build the object-storage key for one receipt image.

    The owning user's id is part of the key, which is what makes cross-user
    access impossible to express: a caller can only ever name keys under its
    own prefix (BRD N2).
    """
    return f"receipts/{user_id}/{file_id}"


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

    def __init__(
        self,
        storage_port: StoragePort | None = None,
        parser_port: ReceiptParserPort | None = None,
        categoriser_port: "ItemCategoriserPort | None" = None,
        repository: "ReceiptRepository | None" = None,
        max_concurrency: int = 2,
        job_timeout_seconds: int = 900,
    ):
        self.storage_port = storage_port
        self.parser_port = parser_port
        self.categoriser_port = categoriser_port
        self.repository = repository
        self.max_concurrency = max_concurrency
        self.job_timeout_seconds = job_timeout_seconds

    def validate_receipt_file(self, content: bytes) -> None:
        """Validate that the file is a supported image format or PDF."""
        kind = filetype.guess(content)

        if kind is None or kind.mime not in self.SUPPORTED_MIME_TYPES:
            # Imported here, not at module scope: `app.api` pulls in the routers,
            # which import this module back (see repository/base.py for the same).
            from app.api.errors import UnsupportedFileFormatError

            raise UnsupportedFileFormatError(
                "Receipts come in as JPEG, PNG, HEIC or a PDF scan. "
                "The other files on this line are fine."
            )

    async def store_receipt_image(self, user: User, content: bytes, content_type: str) -> str:
        """Uploads a receipt image to object storage, tagged with owner ID."""
        if not self.storage_port:
            raise RuntimeError("Storage port not configured.")

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
            except Exception as e:
                import logging

                logging.error(f"HEIC conversion failed in store_receipt_image: {e}")

        file_id = str(uuid.uuid4())
        object_name = receipt_object_name(user.id, file_id)
        metadata = {"owner_id": str(user.id)}

        await self.storage_port.upload_file(object_name, content, content_type, metadata)
        return file_id

    async def get_presigned_url_for_image(self, user: User, file_id: str) -> str:
        """Generates a presigned URL for a receipt image, ensuring ownership."""
        if not self.storage_port:
            raise RuntimeError("Storage port not configured.")

        object_name = receipt_object_name(user.id, file_id)

        from app.services.storage import ObjectNotFoundError

        try:
            await self.storage_port.get_object_metadata(object_name)
        except ObjectNotFoundError:
            raise ObjectNotFoundError(
                f"Image {file_id} not found or you don't have access to it."
            ) from None

        return await self.storage_port.generate_presigned_url(object_name)

    async def process_upload_job_task(
        self, job_id: uuid.UUID, user: User, receipts_data: list[list[dict[str, str | bytes]]]
    ) -> None:
        """Background task: store images in MinIO, then extract via vision LLM.

        Runs after the HTTP response has already been sent.  Opens its own
        database session because the request-scoped one is closed by now.

        Steps:
        1. Upload each file to S3 and collect file_ids.
        2. If a ``ReceiptParserPort`` is configured, download the stored images
           and send them to the vision LLM for structured extraction.
        3. Save the extraction result to ``job.result_data``.

        Extraction is bounded by ``job_timeout_seconds``; on timeout the job is
        marked failed rather than left in PROCESSING for a client to poll forever.
        """
        session_factory = get_session_factory()
        async with session_factory() as session:
            stmt = select(UploadJob).where(UploadJob.id == job_id)
            job = (await session.execute(stmt)).scalar_one_or_none()
            if not job:
                return

            job.status = JobStatus.PROCESSING
            job.total_items = len(receipts_data)
            job.processed_items = 0
            await session.commit()

            try:
                all_file_ids: list[str] = []
                all_extractions: list[dict[str, object]] = []

                categories = await CategoryRepository(session).list_available(user.id)

                async def process_single_receipt(
                    files_data: list[dict[str, str | bytes]],
                ) -> dict[str, object]:
                    file_ids: list[str] = []
                    content_types: list[str] = []
                    for file_data in files_data:
                        content = file_data["content"]
                        content_type = file_data["content_type"]
                        file_id = await self.store_receipt_image(user, content, content_type)  # type: ignore[arg-type]
                        file_ids.append(file_id)
                        content_types.append(str(content_type))

                    extraction: dict[str, object] = {"file_ids": file_ids}
                    if self.parser_port and self.storage_port:
                        ext = await self._run_extraction(user, file_ids, content_types)
                        ext["file_ids"] = file_ids

                        await self._categorise_extraction(ext, categories)
                        extraction = ext

                    return extraction

                semaphore = asyncio.Semaphore(self.max_concurrency)

                async def bound_process(fd: list[dict[str, str | bytes]]) -> dict[str, object]:
                    async with semaphore:
                        return await process_single_receipt(fd)

                tasks = [
                    asyncio.create_task(bound_process(files_data)) for files_data in receipts_data
                ]

                try:
                    async with asyncio.timeout(self.job_timeout_seconds):
                        for completed_task in asyncio.as_completed(tasks):
                            await completed_task
                            job.processed_items += 1
                            await session.commit()
                except BaseException:
                    # Without this the survivors keep uploading and calling the LLM
                    # long after the job has been marked failed.
                    for task in tasks:
                        task.cancel()
                    await asyncio.gather(*tasks, return_exceptions=True)
                    raise

                for extraction in (task.result() for task in tasks):
                    file_ids = cast(list[str], extraction.get("file_ids", []))
                    all_file_ids.extend(file_ids)

                    if self.parser_port and self.storage_port:
                        repo = ReceiptRepository(session).bypass_ownership()
                        is_dup = await repo.has_duplicate(
                            user_id=user.id,
                            merchant_name=cast(str | None, extraction.get("merchant_name")),
                            transaction_date_str=cast(
                                str | None, extraction.get("transaction_date")
                            ),
                            total_amount_str=cast(str | None, extraction.get("receipt_total")),
                        )
                        extraction["is_duplicate"] = is_dup
                        all_extractions.append(extraction)

                job.file_ids = all_file_ids
                if self.parser_port and self.storage_port:
                    job.result_data = {"extractions": all_extractions}

                job.status = JobStatus.COMPLETED
                await session.commit()
            except Exception as e:
                logger.exception("Background task failed")
                await session.rollback()
                job.status = JobStatus.FAILED
                session.add(job)
                await session.commit()
                raise e

    async def _categorise_extraction(
        self,
        extraction: dict[str, object],
        categories: Sequence[Category],
    ) -> None:
        """Add a category to every line item the parser read, in place (BRD C1-C3).

        Works on the raw extraction dict because that is what is persisted to
        `UploadJob.result_data` and replayed to the wizard; the items are parsed
        into `ExtractedLineItem` only so the port receives a typed contract.

        Anything not confidently placed — below the threshold, declined by the
        categoriser, or too mangled to validate — is filed under Uncategorized
        rather than guessed at, which is what puts it in the review queue. The
        categoriser's own confidence is kept so the weak guess stays auditable.
        """
        if not self.categoriser_port or not categories:
            return

        items_data = extraction.get("line_items")
        if not isinstance(items_data, list):
            return

        parsed: list[ExtractedLineItem] = []
        indices: list[int] = []
        for index, raw in enumerate(items_data):
            if not isinstance(raw, dict):
                continue
            try:
                parsed.append(ExtractedLineItem(**raw))
            except ValidationError:
                logger.warning("Line item %s failed validation; filing it as Uncategorized", index)
                continue
            indices.append(index)

        categorised = (
            await self.categoriser_port.categorise_items(parsed, categories) if parsed else []
        )
        by_index = dict(zip(indices, categorised, strict=True))
        uncategorized = next((c for c in categories if c.name == UNCATEGORIZED), None)
        threshold = get_settings().categorization_confidence_threshold

        for index, raw in enumerate(items_data):
            if not isinstance(raw, dict):
                continue
            item = by_index.get(index)
            raw["category_confidence"] = item.category_confidence if item else None
            if item and confident_category(item.category_id, item.category_confidence, threshold):
                raw["category_id"] = str(item.category_id)
                raw["category_name"] = item.category_name
            elif uncategorized is not None:
                raw["category_id"] = str(uncategorized.id)
                raw["category_name"] = uncategorized.name

    async def _run_extraction(
        self, user: User, file_ids: list[str], content_types: list[str]
    ) -> dict[str, object]:
        """Download stored images and send them to the vision parser.

        Returns the extraction result as a plain dict suitable for JSON
        storage in ``UploadJob.result_data``.
        """
        assert self.storage_port is not None
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

            from app.domain.position_matching import (
                ComparisonNotPossible,
                MatchResult,
                are_photos_from_same_receipt,
                match_positions,
            )
            from app.schemas.extraction import PositionMatch

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

    async def delete_receipt(self, receipt_id: uuid.UUID) -> bool:
        """Permanently delete a receipt, its line items and its stored photos.

        Returns False when the receipt does not exist or belongs to someone
        else — the repository's ownership filter makes those two cases
        indistinguishable on purpose (BRD N2).

        Line items go with the row through the database cascade, and any upload
        job that still named these photos has its transient payload discarded so
        the wizard cannot render tiles for images that no longer exist. The
        photos are deleted one by one and a failure on any of them is logged rather than
        raised: orphaned bytes in object storage cost nothing, while letting the
        error roll the transaction back would leave a receipt whose photos are
        already half gone.
        """
        assert self.repository is not None
        assert self.storage_port is not None

        receipt = await self.repository.get(receipt_id)
        if not receipt:
            return False

        owner_id = receipt.user_id
        file_ids = list(receipt.file_ids or [])

        deleted = await self.repository.delete(receipt_id)
        if not deleted:
            return False

        await self.repository.discard_upload_job_payloads(owner_id, file_ids)

        for file_id in file_ids:
            object_name = receipt_object_name(owner_id, file_id)
            try:
                await self.storage_port.delete_file(object_name)
            except Exception:
                logger.exception("Could not delete receipt image %s", object_name)

        return True

    async def edit_extracted_line_item(
        self,
        job_id: uuid.UUID,
        user_id: uuid.UUID,
        request_data: EditLineItemRequest,
    ) -> UploadJobStatusResponse:
        """Correct one extracted line item and re-check the receipt's arithmetic.

        Only the fields the caller actually sent are applied, so an omitted field
        keeps its parsed value while an empty string deliberately clears one
        (BRD A9). The whole extraction is re-validated afterwards, which is what
        recomputes `computed_total` and `items_sum_matches_total` and therefore
        what lets a corrected receipt through the commit gate (BRD A11).

        Raises ValueError when the job, the extraction or the item is unknown.
        """
        assert self.repository is not None
        job = await self.repository.get_upload_job(job_id, user_id)
        if not job:
            raise ValueError("Job not found")

        if not job.result_data or "extractions" not in job.result_data:
            raise ValueError("Job has no extractions")

        extractions = job.result_data["extractions"]
        ext_idx = request_data.extraction_index
        if ext_idx < 0 or ext_idx >= len(extractions):
            raise ValueError("Invalid extraction index")

        extraction = extractions[ext_idx]
        items = extraction.get("line_items", [])
        item_idx = request_data.item_index
        if item_idx < 0 or item_idx >= len(items):
            raise ValueError("Invalid item index")

        changes = request_data.model_dump(exclude_unset=True)
        changes.pop("extraction_index", None)
        changes.pop("item_index", None)
        if not changes:
            raise ValueError("No fields to update")

        items[item_idx] = {**items[item_idx], **changes}
        extraction["line_items"] = items

        # Round-tripping through the schema re-runs normalise_amount on what the
        # user typed and recomputes the totals the commit gate reads.
        parsed = ExtractedReceipt(**extraction)
        updated = parsed.model_dump()
        updated["is_duplicate"] = extraction.get("is_duplicate")
        updated["duplicate_resolved"] = extraction.get("duplicate_resolved")

        extractions[ext_idx] = updated
        job.result_data["extractions"] = extractions
        flag_modified(job, "result_data")

        return UploadJobStatusResponse(
            job_id=job.id,
            file_ids=job.file_ids,
            status=job.status,
            extracted_data=job.result_data,
            total_items=job.total_items or 0,
            processed_items=job.processed_items or 0,
        )

    async def update_receipt(
        self, receipt_id: uuid.UUID, request_data: UpdateReceiptRequest
    ) -> Receipt | None:
        """Correct a stored receipt's header and line items (BRD A9, A11, D6).

        Replaces the whole line-item list rather than diffing it: an existing
        line resent with its id is updated in place, one without an id is
        created, and an existing id that is not resent is deleted through the
        ``delete-orphan`` cascade on ``Receipt.line_items``.

        Returns None when the receipt does not exist or belongs to someone else
        — the repository's ownership filter makes the two indistinguishable on
        purpose (BRD N2).

        Raises DomainError when the line totals do not sum to `total_amount`,
        the same invariant the upload wizard's commit gate enforces (BRD A9):
        a stored receipt must never disagree with its own line items.
        """
        assert self.repository is not None

        receipt = await self.repository.get_with_items(receipt_id)
        if not receipt:
            return None

        computed = sum((item.total_price for item in request_data.line_items), start=Decimal("0"))

        from app.models.receipt import ReceiptStatus

        if computed != request_data.total_amount:
            # The sum does not match, but we let the user store it anyway as NEEDS_REVIEW.
            receipt.status = ReceiptStatus.MANUAL_REVIEW
        else:
            # If they fixed the sums, it's valid again.
            receipt.status = ReceiptStatus.PARSED

        receipt.merchant_name = request_data.merchant_name
        receipt.transaction_date = (
            datetime.combine(request_data.transaction_date, datetime.min.time(), tzinfo=UTC)
            if request_data.transaction_date
            else None
        )
        receipt.total_amount = request_data.total_amount

        existing_by_id = {item.id: item for item in receipt.line_items}
        sent_ids = {item.id for item in request_data.line_items if item.id is not None}
        unknown_ids = sent_ids - existing_by_id.keys()
        if unknown_ids:
            raise ValueError(f"Line item(s) not found on this receipt: {unknown_ids}")

        updated_items: list[LineItem] = []
        for line in request_data.line_items:
            if line.id is not None:
                existing = existing_by_id[line.id]
                existing.name = line.name
                existing.quantity = line.quantity
                existing.unit_price = line.unit_price
                existing.total_price = line.total_price
                updated_items.append(existing)
            else:
                updated_items.append(
                    LineItem(
                        name=line.name,
                        quantity=line.quantity,
                        unit_price=line.unit_price,
                        total_price=line.total_price,
                    )
                )

        # Reassigning the collection is what lets delete-orphan drop any
        # existing line the caller did not resend.
        receipt.line_items = updated_items

        await self.repository.session.flush()
        return receipt

    async def resolve_position_match(
        self,
        job_id: uuid.UUID,
        user_id: uuid.UUID,
        request_data: ResolvePositionMatchRequest,
    ) -> UploadJobStatusResponse:
        assert self.repository is not None
        job = await self.repository.get_upload_job(job_id, user_id)
        if not job:
            raise ValueError("Job not found")

        if not job.result_data or "extractions" not in job.result_data:
            raise ValueError("Job has no extractions")

        extractions = job.result_data["extractions"]
        ext_idx = request_data.extraction_index
        if ext_idx < 0 or ext_idx >= len(extractions):
            raise ValueError("Invalid extraction index")

        extraction = extractions[ext_idx]
        matches = extraction.get("position_matches", [])
        match_idx = request_data.match_index

        if match_idx < 0 or match_idx >= len(matches):
            raise ValueError("Invalid match index")

        match_dict = matches[match_idx]
        old_result = match_dict.get("result")
        new_result = request_data.action

        if old_result != new_result:
            match_dict["result"] = new_result
            match_dict["user_overridden"] = True
            extraction["position_matches"][match_idx] = match_dict

            parsed = ExtractedReceipt(**extraction)

            updated_extraction = copy.deepcopy(extraction)
            updated_extraction["computed_total"] = str(parsed.computed_total)
            updated_extraction["items_sum_matches_total"] = parsed.items_sum_matches_total
            updated_extraction["requires_manual_review"] = parsed.requires_manual_review

            extractions[ext_idx] = updated_extraction
            job.result_data["extractions"] = extractions
            flag_modified(job, "result_data")

            override = PositionMatchOverride(
                user_id=user_id,
                job_id=job.id,
                extraction_index=ext_idx,
                match_index=match_idx,
                original_result=old_result or "unknown",
                corrected_result=new_result,
            )
            await self.repository.add_position_match_override(override)

        return UploadJobStatusResponse(
            job_id=job.id,
            file_ids=job.file_ids,
            status=job.status,
            extracted_data=job.result_data,
            total_items=job.total_items or 0,
            processed_items=job.processed_items or 0,
        )
