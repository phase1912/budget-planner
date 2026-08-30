import uuid
from typing import Any, Literal

from pydantic import BaseModel

from app.models.upload_job import JobStatus


class UploadReceiptResponse(BaseModel):
    """Response returned upon successful receipt upload."""

    message: str
    job_id: uuid.UUID


class UploadJobStatusResponse(BaseModel):
    """Current status of an asynchronous receipt upload job.

    Once the job completes, ``extracted_data`` contains the structured
    extraction output (an ``ExtractedReceipt`` dict) for the "What we read"
    wizard screen.
    """

    job_id: uuid.UUID
    status: JobStatus
    file_ids: list[str]
    extracted_data: dict[str, Any] | None = None


class ResolveDuplicateRequest(BaseModel):
    """Request to resolve a duplicate receipt extraction."""

    extraction_index: int
    action: Literal["store", "skip"]
