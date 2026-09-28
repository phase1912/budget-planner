import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Model


class ExportKind(enum.StrEnum):
    """What an export holds: the receipts list, or the statistics table (BRD N6)."""

    RECEIPTS = "receipts"
    STATISTICS = "statistics"


class ExportFormat(enum.StrEnum):
    """The file format asked for (BRD N6: CSV or JSON)."""

    CSV = "csv"
    JSON = "json"


class ExportStatus(enum.StrEnum):
    """Where an export stands: waiting, being written, ready to download, or failed."""

    PENDING = "pending"
    RUNNING = "running"
    READY = "ready"
    FAILED = "failed"


def _stored_as_text(kind: type[enum.StrEnum], name: str) -> Enum:
    return Enum(kind, name=name, native_enum=False, length=16, values_callable=_values)


def _values(kind: type[enum.StrEnum]) -> list[str]:
    return [member.value for member in kind]


class ExportJob(Model):
    """One export of the user's data, written in the background (BRD N6 — F7.6).

    `params` are the filters of the screen it was asked from — the receipts list's
    dates, status and search, or the statistics period and comparison — so the file
    holds what the screen showed. The finished file lives in object storage under
    the owner's prefix (`object_name`); `error` says why a failed one failed.
    """

    __tablename__ = "export_jobs"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kind: Mapped[ExportKind] = mapped_column(_stored_as_text(ExportKind, "export_kind"))
    format: Mapped[ExportFormat] = mapped_column(_stored_as_text(ExportFormat, "export_format"))
    params: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[ExportStatus] = mapped_column(
        _stored_as_text(ExportStatus, "export_status"), default=ExportStatus.PENDING
    )
    object_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    error: Mapped[str | None] = mapped_column(String(500), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
