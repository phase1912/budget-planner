import uuid

from pydantic import BaseModel

from app.models.upload_job import JobStatus


class UploadReceiptResponse(BaseModel):
    """Response returned upon successful receipt upload."""

    message: str
    job_id: uuid.UUID


class UploadJobStatusResponse(BaseModel):
    """Current status of an asynchronous receipt upload job."""

    job_id: uuid.UUID
    status: JobStatus
    file_ids: list[str]
