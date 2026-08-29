import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Numeric, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Model

if TYPE_CHECKING:
    from app.models.line_item import LineItem


class ReceiptStatus(enum.StrEnum):
    """Lifecycle states of a receipt."""

    UPLOADED = "uploaded"
    PARSING = "parsing"
    PARSED = "parsed"
    MANUAL_REVIEW = "manual_review"
    FAILED = "failed"


class Receipt(Model):
    """One purchase transaction, from one or more photos."""

    __tablename__ = "receipts"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    merchant_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    transaction_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    total_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    status: Mapped[ReceiptStatus] = mapped_column(
        Enum(ReceiptStatus, name="receipt_status_enum", create_type=False),
        default=ReceiptStatus.UPLOADED,
        nullable=False,
    )
    file_ids: Mapped[list[str]] = mapped_column(
        JSONB,
        default=list,
        server_default=text("'[]'::jsonb"),
        nullable=False,
    )
    processing_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    parser_version: Mapped[str | None] = mapped_column(String(50), nullable=True)

    line_items: Mapped[list["LineItem"]] = relationship(
        "LineItem", back_populates="receipt", cascade="all, delete-orphan"
    )
