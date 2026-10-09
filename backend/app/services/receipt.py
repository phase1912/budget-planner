import asyncio
import copy
import logging
import uuid
from collections.abc import Sequence
from datetime import UTC, date, datetime, time
from decimal import Decimal
from typing import Any, cast

import filetype  # type: ignore[import-untyped]
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm.attributes import flag_modified

from app.adapters.photo_ingestion import PhotoIngestionAdapter
from app.core.config import get_settings
from app.db.session import get_session_factory
from app.domain.categories import UNCATEGORIZED, confident_category, match_rule
from app.domain.discounts import (
    WHOLE_RECEIPT_DISCOUNT,
    dominant_category,
    file_discounts_with_products,
    printed_amount,
)
from app.domain.receipt_dates import with_upload_date
from app.domain.receipt_reconciliation import (
    Reconciliation,
    accepts_recheck,
    reconcile_by_rules,
)
from app.domain.receipt_totals import lines_match_total
from app.models.category import Category
from app.models.category_rule import CategoryRule
from app.models.line_item import LineItem
from app.models.match_override import PositionMatchOverride
from app.models.receipt import Receipt
from app.models.upload_job import JobStatus, UploadJob
from app.models.user import User
from app.ports.categorisation import ItemCategoriserPort
from app.ports.ingestion import ReceiptIngestionPort, UploadedFile
from app.ports.parsing import CURRENT_PARSER_VERSION, ReceiptParserPort, ReceiptRecheckerPort
from app.ports.storage import StoragePort, receipt_object_name
from app.repository.category import CategoryRepository
from app.repository.receipt import ReceiptRepository
from app.schemas.extraction import ExtractedLineItem, ExtractedReceipt
from app.schemas.receipt import (
    AddDiscountRequest,
    EditLineItemRequest,
    ResolvePositionMatchRequest,
    UpdateReceiptRequest,
    UploadJobStatusResponse,
)

logger = logging.getLogger(__name__)

RECHECK_ATTEMPTS = 2
"""Second looks the model gets at a receipt whose lines miss its total (BRD A9).

The second sees what the first got wrong; a third rarely finds what two did not, and
each costs a model call and the user's wait.
"""


def _reading_fields(extraction: dict[str, object]) -> dict[str, Any]:
    return {k: v for k, v in extraction.items() if k in ExtractedReceipt.model_fields}


def _dated(extraction: dict[str, object], today: date) -> dict[str, object]:
    """The reading dated by its upload day if it had no date, with its review flag
    recomputed: a missing date no longer holds a receipt back (BRD A11, D3)."""
    dated = with_upload_date(extraction, today)
    if dated is extraction:
        return extraction
    validated = ExtractedReceipt(**_reading_fields(dated)).model_dump()
    return {**dated, "requires_manual_review": validated["requires_manual_review"]}


def _settled(extraction: dict[str, object], how: Reconciliation) -> dict[str, object]:
    """A corrected reading with its sums recomputed and how it was corrected recorded."""
    validated = ExtractedReceipt(**_reading_fields(extraction)).model_dump()
    return {**extraction, **validated, "total_reconciled_by": how.value}


def _redated(stored: datetime | None, day: date | None) -> datetime | None:
    """Move a purchase to `day` while keeping the time printed on the receipt.

    The edit dialog only carries a date, so the time of day comes from what is
    already stored; a receipt that had no date starts at midnight. The value
    stays the shop's wall clock labelled UTC (ADR-0009).
    """
    if day is None:
        return None
    time_of_day = stored.timetz() if stored is not None else time(tzinfo=UTC)
    return datetime.combine(day, time_of_day)


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
        rechecker_port: ReceiptRecheckerPort | None = None,
        categoriser_port: "ItemCategoriserPort | None" = None,
        repository: "ReceiptRepository | None" = None,
        max_concurrency: int = 2,
        job_timeout_seconds: int = 900,
    ):
        self.storage_port = storage_port
        self.parser_port = parser_port
        self.rechecker_port = rechecker_port
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

                category_repository = CategoryRepository(session)
                categories = await category_repository.list_available(user.id)
                rules = await category_repository.list_rules(user.id)

                if self.storage_port is None:
                    raise RuntimeError("Storage port not configured.")
                photos = PhotoIngestionAdapter(self.storage_port, self.parser_port)

                async def process_single_receipt(
                    files_data: list[dict[str, str | bytes]],
                ) -> dict[str, object]:
                    uploads = cast(list[UploadedFile], files_data)
                    extraction = (await photos.ingest(user, uploads)).extraction
                    extraction = await self._reconcile_total(user, extraction)
                    extraction = _dated(extraction, datetime.now(UTC).date())
                    if self.parser_port:
                        await self._categorise_extraction(extraction, categories, rules)
                        self._file_discount_lines(extraction)
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

    async def store_from_channel[PayloadT](
        self,
        user: User,
        ingestion: ReceiptIngestionPort[PayloadT],
        payload: PayloadT,
        source_reference: str | None,
    ) -> None:
        """Background task: read a receipt that arrived without the upload wizard, and keep it.

        Used by intake channels with no one at a screen to confirm what was read
        (F11.2): the receipt is categorised like an upload, with the user's
        rules, and stored straight away; anything uncertain lands in review.
        A `source_reference` already stored for this channel is skipped, so a
        message delivered twice is one receipt.
        """
        session_factory = get_session_factory()
        async with session_factory() as session:
            receipts = ReceiptRepository(session).bypass_ownership()
            if source_reference and await receipts.has_source_reference(
                user.id, ingestion.channel, source_reference
            ):
                return
            result = await ingestion.ingest(user, payload)
            extraction = await self._reconcile_total(user, result.extraction)
            extraction = _dated(extraction, datetime.now(UTC).date())
            if "error" in extraction:
                extraction["requires_manual_review"] = True
            else:
                category_repository = CategoryRepository(session)
                await self._categorise_extraction(
                    extraction,
                    await category_repository.list_available(user.id),
                    await category_repository.list_rules(user.id),
                )
                self._file_discount_lines(extraction)
            receipts.create_from_extraction(
                user_id=user.id,
                file_ids=result.file_ids,
                extraction=extraction,
                parser_version=CURRENT_PARSER_VERSION,
                channel=ingestion.channel,
                source_reference=source_reference,
            )
            await session.commit()

    async def _reconcile_total(
        self, user: User, extraction: dict[str, object]
    ) -> dict[str, object]:
        """Make a reading's lines agree with its total before anyone is asked (BRD A9, A11).

        Known causes are fixed by rule (`reconcile_by_rules`); otherwise the model looks
        at the stored photos again, up to RECHECK_ATTEMPTS times, each time told how far
        off the last reading was, and a new reading is kept only if it agrees with the
        same total (`accepts_recheck`). What still disagrees is marked `unresolved`, so
        the wizard can say the app already tried. Never raises: a failed recheck leaves
        the first reading as it was.
        """
        if "error" in extraction or extraction.get("items_sum_matches_total") is not False:
            return extraction
        ruled = reconcile_by_rules(extraction)
        if ruled is not None:
            return _settled(*reversed(ruled))
        latest = extraction
        can_recheck = bool(self.rechecker_port and self.storage_port and extraction.get("file_ids"))
        for _ in range(RECHECK_ATTEMPTS if can_recheck else 0):
            assert self.rechecker_port is not None
            try:
                images, types = await self._stored_photos(user, latest)
                reading = ExtractedReceipt(**_reading_fields(latest))
                after = (
                    await self.rechecker_port.recheck(images, mime_types=types, reading=reading)
                ).model_dump()
            except Exception:
                logger.exception("Rechecking a receipt for user %s failed", user.id)
                break
            after["file_ids"] = extraction.get("file_ids", [])
            if accepts_recheck(extraction, after):
                return _settled(after, Reconciliation.RECHECKED)
            latest = after
        return {**extraction, "total_reconciled_by": Reconciliation.UNRESOLVED.value}

    async def _stored_photos(
        self, user: User, extraction: dict[str, object]
    ) -> tuple[list[bytes], list[str]]:
        assert self.storage_port is not None
        file_ids = cast(list[str], extraction.get("file_ids") or [])
        images = [
            await self.storage_port.download_file(receipt_object_name(user.id, file_id))
            for file_id in file_ids
        ]
        return images, [filetype.guess_mime(image) or "image/jpeg" for image in images]

    @staticmethod
    def _file_discount_lines(extraction: dict[str, object]) -> None:
        """Give each "Rabat"/"OPUST" line the category of the product it reduces, in place.

        Runs after categorisation, so it overrides whatever the categoriser made of
        a negative line (see `app.domain.discounts`). The lines stay separate.
        """
        items = extraction.get("line_items")
        if isinstance(items, list):
            extraction["line_items"] = file_discounts_with_products(items)

    async def _categorise_extraction(
        self,
        extraction: dict[str, object],
        categories: Sequence[Category],
        rules: Sequence[CategoryRule] = (),
    ) -> None:
        """Add a category to every line item the parser read, in place (BRD C1-C3, C5).

        Works on the raw extraction dict because that is what is persisted to
        `UploadJob.result_data` and replayed to the wizard; the items are parsed
        into `ExtractedLineItem` only so the port receives a typed contract.

        The user's correction rules go first and need no categoriser at all. The
        rest go to the categoriser, and anything it does not confidently place —
        below the threshold, declined, or too mangled to validate — is filed under
        Uncategorized rather than guessed at, which puts it in the review queue.
        """
        if not categories:
            return
        items_data = extraction.get("line_items")
        if not isinstance(items_data, list):
            return

        by_id = {category.id: category for category in categories}
        merchant = extraction.get("merchant_name")
        merchant_name = merchant if isinstance(merchant, str) else None
        ruled: set[int] = set()
        for index, raw in enumerate(items_data):
            if not isinstance(raw, dict):
                continue
            chosen = match_rule(str(raw.get("name") or ""), merchant_name, rules)
            if chosen in by_id:
                raw["category_id"] = str(chosen)
                raw["category_name"] = by_id[chosen].name
                raw["category_confidence"] = None
                ruled.add(index)

        if not self.categoriser_port:
            return

        parsed: list[ExtractedLineItem] = []
        indices: list[int] = []
        for index, raw in enumerate(items_data):
            if not isinstance(raw, dict) or index in ruled:
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
            if not isinstance(raw, dict) or index in ruled:
                continue
            item = by_index.get(index)
            raw["category_confidence"] = item.category_confidence if item else None
            if item and confident_category(item.category_id, item.category_confidence, threshold):
                raw["category_id"] = str(item.category_id)
                raw["category_name"] = item.category_name
            elif uncategorized is not None:
                raw["category_id"] = str(uncategorized.id)
                raw["category_name"] = uncategorized.name

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
        job, extractions, extraction = await self._extraction(
            job_id, user_id, request_data.extraction_index
        )
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
        return self._recheck(job, extractions, request_data.extraction_index, extraction)

    async def add_extracted_discount(
        self, job_id: uuid.UUID, user_id: uuid.UUID, request_data: AddDiscountRequest
    ) -> UploadJobStatusResponse:
        """Add a discount the reader missed to an extracted receipt (BRD A9, A11).

        The line goes last, named WHOLE_RECEIPT_DISCOUNT, and is filed under the
        receipt's dominant category: it reduces the bill, not one product. The
        arithmetic is re-checked, so a receipt it reconciles passes the commit gate.

        Raises ValueError when the job or the extraction is unknown.
        """
        job, extractions, extraction = await self._extraction(
            job_id, user_id, request_data.extraction_index
        )
        items = list(extraction.get("line_items", []))
        by_category = {str(i.get("category_id")): i for i in items if i.get("category_id")}
        category = dominant_category(
            (
                str(i["category_id"]) if i.get("category_id") else None,
                printed_amount(i.get("total_price")) or Decimal(0),
            )
            for i in items
        )
        amount = str(request_data.amount)
        items.append(
            {
                "name": WHOLE_RECEIPT_DISCOUNT,
                "quantity": "1",
                "unit_price": amount,
                "total_price": amount,
                "confidence": 100,
                "file_id": items[-1].get("file_id") if items else None,
                "category_id": category,
                "category_name": by_category[category].get("category_name") if category else None,
                "category_confidence": 100 if category else None,
            }
        )
        extraction["line_items"] = items
        return self._recheck(job, extractions, request_data.extraction_index, extraction)

    async def _extraction(
        self, job_id: uuid.UUID, user_id: uuid.UUID, index: int
    ) -> tuple[UploadJob, list[dict[str, Any]], dict[str, Any]]:
        """The user's upload job, its extractions and the one at `index`; ValueError if none."""
        assert self.repository is not None
        job = await self.repository.get_upload_job(job_id, user_id)
        if not job:
            raise ValueError("Job not found")
        if not job.result_data or "extractions" not in job.result_data:
            raise ValueError("Job has no extractions")
        extractions = job.result_data["extractions"]
        if index < 0 or index >= len(extractions):
            raise ValueError("Invalid extraction index")
        return job, extractions, extractions[index]

    @staticmethod
    def _recheck(
        job: UploadJob,
        extractions: list[dict[str, Any]],
        index: int,
        extraction: dict[str, Any],
    ) -> UploadJobStatusResponse:
        """Store a changed extraction with its arithmetic recomputed, and answer with the job."""
        # Round-tripping through the schema re-runs normalise_amount on what the
        # user typed and recomputes the totals the commit gate reads. JSON mode,
        # because the column is JSON: a category id must go back as text, not a UUID.
        updated = ExtractedReceipt(**extraction).model_dump(mode="json")
        updated["is_duplicate"] = extraction.get("is_duplicate")
        updated["duplicate_resolved"] = extraction.get("duplicate_resolved")
        extractions[index] = updated
        assert job.result_data is not None
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

        A receipt whose lines add up to `total_amount`, within a grosz, counts
        toward the month again (`parsed`); one that still disagrees is kept but
        held out as `manual_review`, the same rule as at upload (BRD A9, A11, D3).
        """
        assert self.repository is not None

        receipt = await self.repository.get_with_items(receipt_id)
        if not receipt:
            return None

        computed = sum((item.total_price for item in request_data.line_items), start=Decimal("0"))

        from app.models.receipt import ReceiptStatus

        receipt.status = (
            ReceiptStatus.PARSED
            if lines_match_total(computed, request_data.total_amount)
            else ReceiptStatus.MANUAL_REVIEW
        )

        receipt.merchant_name = request_data.merchant_name
        receipt.transaction_date = _redated(receipt.transaction_date, request_data.transaction_date)
        receipt.total_amount = request_data.total_amount

        existing_by_id = {item.id: item for item in receipt.line_items}
        sent_ids = {item.id for item in request_data.line_items if item.id is not None}
        unknown_ids = sent_ids - existing_by_id.keys()
        if unknown_ids:
            raise ValueError(f"Line item(s) not found on this receipt: {unknown_ids}")

        updated_items: list[LineItem] = []
        new_items: list[LineItem] = []
        for line in request_data.line_items:
            if line.id is not None:
                existing = existing_by_id[line.id]
                existing.name = line.name
                existing.quantity = line.quantity
                existing.unit_price = line.unit_price
                existing.total_price = line.total_price
                updated_items.append(existing)
            else:
                added = LineItem(
                    name=line.name,
                    quantity=line.quantity,
                    unit_price=line.unit_price,
                    total_price=line.total_price,
                )
                new_items.append(added)
                updated_items.append(added)

        # A discount typed in by the user reduces the bill, not one product: file
        # it where most of the money went rather than leave it to categorise.
        category = dominant_category((i.category_id, i.total_price) for i in updated_items)
        for item in new_items:
            if item.total_price < 0 and item.category_id is None:
                item.category_id = category

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
