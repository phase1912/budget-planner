import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field

from app.models.export_job import ExportFormat, ExportKind, ExportStatus
from app.models.receipt import ReceiptStatus


class ExportRequest(BaseModel):
    """What to export, in which format, filtered as the screen it came from (BRD N6).

    For `receipts`: the list's filters — `start`/`end` (both included), `status`
    and the search `q` — all optional. For `statistics`: the period, which is
    required, and whether it is compared with the previous one.
    """

    kind: ExportKind
    format: ExportFormat
    start: date | None = None
    end: date | None = None
    status: ReceiptStatus | None = None
    q: str | None = Field(None, max_length=200)
    compare: bool = False


class ExportJobResponse(BaseModel):
    """An export's progress; once `status` is `ready`, its file can be downloaded."""

    id: uuid.UUID
    kind: ExportKind
    format: ExportFormat
    status: ExportStatus
    filename: str
    error: str | None
    created_at: datetime
    completed_at: datetime | None

    model_config = {"from_attributes": True}
