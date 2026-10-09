import enum
import uuid
from typing import Any

from sqlalchemy import JSON, Enum, ForeignKey, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Model
from app.models.receipt import ReceiptChannel


class JobStatus(enum.StrEnum):
    """Lifecycle states of an asynchronous upload job."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    STORED = "stored"
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
        server_default=text("'[]'::json"),
        nullable=False,
    )
    result_data: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        default=None,
        nullable=True,
    )
    # The intake the job's receipts arrived through, handed on to the receipts it stores
    # (F11.1.4); the upload wizard is the photo channel's.
    channel: Mapped[ReceiptChannel] = mapped_column(
        Enum(ReceiptChannel, name="receipt_channel_enum", create_type=False),
        default=ReceiptChannel.PHOTO,
        server_default=ReceiptChannel.PHOTO.name,
        nullable=False,
    )
    total_items: Mapped[int] = mapped_column(default=0, server_default=text("0"), nullable=False)
    processed_items: Mapped[int] = mapped_column(
        default=0, server_default=text("0"), nullable=False
    )
