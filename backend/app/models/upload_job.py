import enum
import uuid

from sqlalchemy import JSON, Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Model


class JobStatus(enum.StrEnum):
    """Lifecycle states of an asynchronous upload job."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class UploadJob(Model):
    """Tracks the status of an asynchronous receipt upload/parsing job."""

    __tablename__ = "upload_jobs"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, name="job_status_enum", create_type=False),
        default=JobStatus.PENDING,
        nullable=False,
    )
    # file_ids will store the resulting MinIO object UUIDs once the job completes.
    # In E3, this might evolve to store the actual structured Receipt IDs.
    file_ids: Mapped[list[str]] = mapped_column(
        JSON,
        default=list,
        server_default="[]",
        nullable=False,
    )
