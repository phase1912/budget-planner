import enum
import uuid
from typing import Any

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
    """Tracks the status of an asynchronous receipt upload/parsing job.

    ``result_data`` stores the structured extraction output (an
    ``ExtractedReceipt`` dict) once the vision LLM finishes.  It lives on the
    job rather than a separate entity because the data is transient — it is
    shown on the wizard's "What we read" screen and then persisted to proper
    Receipt/LineItem entities on the "Resolve" step.
    """

    __tablename__ = "upload_jobs"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, name="job_status_enum", create_type=False),
        default=JobStatus.PENDING,
        nullable=False,
    )
    file_ids: Mapped[list[str]] = mapped_column(
        JSON,
        default=list,
        server_default="[]",
        nullable=False,
    )
    result_data: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        default=None,
        nullable=True,
    )
