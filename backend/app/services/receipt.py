import copy
import logging
import uuid
from typing import Any, cast

import filetype  # type: ignore[import-untyped]
from sqlalchemy import select
from sqlalchemy.orm.attributes import flag_modified

from app.api.errors import UnsupportedFileFormatError
from app.db.session import get_session_factory
from app.models.match_override import PositionMatchOverride
from app.models.upload_job import JobStatus, UploadJob
from app.models.user import User
from app.ports.parsing import ReceiptParserPort
from app.ports.storage import StoragePort
from app.repository.receipt import ReceiptRepository
from app.schemas.extraction import ExtractedReceipt
from app.schemas.receipt import ResolvePositionMatchRequest, UploadJobStatusResponse

logger = logging.getLogger(__name__)


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
        repository: "ReceiptRepository | None" = None,
    ):
        self.storage_port = storage_port
        self.parser_port = parser_port
        self.repository = repository

    def validate_receipt_file(self, content: bytes) -> None:
        """Validate that the file is a supported image format or PDF."""
        kind = filetype.guess(content)

        if kind is None or kind.mime not in self.SUPPORTED_MIME_TYPES:
            raise UnsupportedFileFormatError(
                "Receipts come in as JPEG, PNG, HEIC or a PDF scan. "
                "The other files on this line are fine."
            )

    async def store_receipt_image(self, user: User, content: bytes, content_type: str) -> str:
        """Uploads a receipt image to object storage, tagged with owner ID."""
        if not self.storage_port:
            raise RuntimeError("Storage port not configured.")

        file_id = str(uuid.uuid4())
        object_name = f"receipts/{user.id}/{file_id}"
        metadata = {"owner_id": str(user.id)}

        await self.storage_port.upload_file(object_name, content, content_type, metadata)
        return file_id

    async def get_presigned_url_for_image(self, user: User, file_id: str) -> str:
        """Generates a presigned URL for a receipt image, ensuring ownership."""
        if not self.storage_port:
            raise RuntimeError("Storage port not configured.")

        object_name = f"receipts/{user.id}/{file_id}"

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
        """
        session_factory = get_session_factory()
        async with session_factory() as session:
            stmt = select(UploadJob).where(UploadJob.id == job_id)
            job = (await session.execute(stmt)).scalar_one_or_none()
            if not job:
                return

            job.status = JobStatus.PROCESSING
            await session.commit()

            try:
                all_file_ids: list[str] = []
                all_extractions: list[dict[str, object]] = []

                for files_data in receipts_data:
                    file_ids: list[str] = []
                    content_types: list[str] = []
                    for file_data in files_data:
                        content = file_data["content"]
                        content_type = file_data["content_type"]

                        file_id = await self.store_receipt_image(user, content, content_type)  # type: ignore[arg-type]
                        file_ids.append(file_id)
                        content_types.append(str(content_type))

                    all_file_ids.extend(file_ids)

                    if self.parser_port and self.storage_port:
                        extraction = await self._run_extraction(user, file_ids, content_types)
                        extraction["file_ids"] = file_ids
                        all_extractions.append(extraction)

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

                        if not is_dup:
                            repo.create_from_extraction(
                                user_id=user.id,
                                file_ids=file_ids,
                                extraction=extraction,
                                parser_version="1.0.0",  # TODO: Get from parser
                            )

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
            object_name = f"receipts/{user.id}/{file_id}"
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
        )
