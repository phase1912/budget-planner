import logging
import uuid

import filetype  # type: ignore[import-untyped]
from sqlalchemy import select

from app.api.errors import UnsupportedFileFormatError
from app.db.session import get_session_factory
from app.models.upload_job import JobStatus, UploadJob
from app.models.user import User
from app.ports.parsing import ReceiptParserPort
from app.ports.storage import StoragePort

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
    ):
        self.storage_port = storage_port
        self.parser_port = parser_port

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
        self, job_id: uuid.UUID, user: User, files_data: list[dict[str, str | bytes]]
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
                file_ids: list[str] = []
                content_types: list[str] = []
                for file_data in files_data:
                    content = file_data["content"]
                    content_type = file_data["content_type"]

                    file_id = await self.store_receipt_image(user, content, content_type)  # type: ignore[arg-type]
                    file_ids.append(file_id)
                    content_types.append(str(content_type))

                job.file_ids = file_ids

                if self.parser_port and self.storage_port:
                    extraction = await self._run_extraction(user, file_ids, content_types)
                    job.result_data = extraction

                job.status = JobStatus.COMPLETED
                await session.commit()
            except Exception:
                job.status = JobStatus.FAILED
                await session.commit()
                raise

    async def _run_extraction(
        self, user: User, file_ids: list[str], content_types: list[str]
    ) -> dict[str, object]:
        """Download stored images and send them to the vision parser.

        Returns the extraction result as a plain dict suitable for JSON
        storage in ``UploadJob.result_data``.
        """
        assert self.storage_port is not None
        assert self.parser_port is not None

        images: list[bytes] = []
        mime_types: list[str] = []
        for file_id, ct in zip(file_ids, content_types, strict=True):
            object_name = f"receipts/{user.id}/{file_id}"
            image_bytes = await self.storage_port.download_file(object_name)
            images.append(image_bytes)
            mime_types.append(ct)

        try:
            result = await self.parser_port.parse(images, mime_types=mime_types)
            return result.model_dump()
        except Exception:
            logger.exception("Vision extraction failed for user %s", user.id)
            return {"error": "extraction_failed"}
