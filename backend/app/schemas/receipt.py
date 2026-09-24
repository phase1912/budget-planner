import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import AliasPath, BaseModel, ConfigDict, Field, computed_field

from app.core.config import get_settings
from app.domain.categories import is_low_confidence
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
    total_items: int = 0
    processed_items: int = 0


class ResolveDuplicateRequest(BaseModel):
    """Request to resolve a duplicate receipt extraction."""

    extraction_index: int
    action: Literal["store", "skip"]


class ResolvePositionMatchRequest(BaseModel):
    """Request to override an automatic position match decision (BRD B7)."""

    extraction_index: int
    match_index: int
    action: Literal["same", "different"]


class ResolveTotalRequest(BaseModel):
    """Request to resolve a missing or low-confidence total."""

    extraction_index: int
    receipt_total: str


class EditLineItemRequest(BaseModel):
    """Correct one line item the parser misread, before anything is stored (BRD A9, A11).

    Every field is optional and `None` means "leave it alone". An empty string is
    a real value meaning "there is no readable amount here", which is what the
    parser itself returns for a line it could not price — so the two cannot be
    collapsed. Callers must send only the fields they are changing.
    """

    extraction_index: int
    item_index: int
    name: str | None = None
    quantity: str | None = None
    unit_price: str | None = None
    total_price: str | None = None


class LineItemInput(BaseModel):
    """One line item in an `UpdateReceiptRequest`.

    An existing line carries its `id`; a new line omits it. An existing id that
    is not resent is deleted, so the request represents the receipt's *entire*
    desired line-item list, not a diff.
    """

    id: uuid.UUID | None = None
    name: str
    quantity: Decimal
    unit_price: Decimal
    total_price: Decimal


class UpdateReceiptRequest(BaseModel):
    """Correct a stored receipt's header and line items (BRD A9, A11, D6).

    Represents the receipt's full desired state, mirroring what the detail
    dialog already shows the user — not a partial patch. `total_amount` must
    equal the sum of `line_items`' totals, the same invariant enforced when the
    receipt was first stored; the two are never allowed to drift apart here
    either.
    """

    merchant_name: str | None
    transaction_date: date | None
    total_amount: Decimal
    line_items: list[LineItemInput]


class CommitJobRequest(BaseModel):
    """Request to commit selected extractions to the database."""

    indices_to_store: list[int]


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
    category_confidence: int | None = None

    model_config = ConfigDict(from_attributes=True)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def category_is_low_confidence(self) -> bool:
        """Whether the category needs a human look before it is trusted (BRD C3).

        Decided server-side against `Settings.categorization_confidence_threshold`
        so the browser renders a verdict instead of recomputing one from a
        threshold ADR-0005 says must not be restated at a call site.
        """
        return is_low_confidence(
            self.category_confidence,
            get_settings().categorization_confidence_threshold,
        )


class ReviewQueueItemResponse(LineItemResponse):
    """A line item waiting in the categorisation review queue (BRD C2, C3).

    Carries its receipt's merchant and date so the queue can be read without
    opening each receipt. The date stays a timestamp: receipts store the
    printed time too, and truncating is the browser's formatting decision.
    """

    receipt_id: uuid.UUID
    merchant_name: str | None = Field(
        default=None, validation_alias=AliasPath("receipt", "merchant_name")
    )
    transaction_date: datetime | None = Field(
        default=None, validation_alias=AliasPath("receipt", "transaction_date")
    )


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
