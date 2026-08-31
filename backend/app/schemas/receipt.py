import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

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


class CategoryResponse(BaseModel):
    id: uuid.UUID
    name: str

    model_config = ConfigDict(from_attributes=True)


class LineItemResponse(BaseModel):
    """Schema for a single line item on a receipt."""

    id: uuid.UUID
    name: str
    quantity: Decimal
    unit_price: Decimal
    total_price: Decimal
    category_id: uuid.UUID | None
    category: CategoryResponse | None = None

    model_config = ConfigDict(from_attributes=True)


class ReceiptResponse(BaseModel):
    """Schema for a receipt list item."""

    id: uuid.UUID
    merchant_name: str | None
    transaction_date: datetime | None
    total_amount: Decimal | None
    status: str
    file_ids: list[str]
    created_at: datetime
    line_items: list[LineItemResponse] = []

    model_config = ConfigDict(from_attributes=True)


class ReceiptDetailResponse(ReceiptResponse):
    """Schema for a receipt with its full line items."""

    pass


class PaginatedReceiptsResponse(BaseModel):
    """Paginated list of receipts."""

    items: list[ReceiptResponse]
    total: int
    page: int
    size: int
    pages: int
