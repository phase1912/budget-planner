import enum
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.orderinglist import ordering_list
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


class ReceiptChannel(enum.StrEnum):
    """How a receipt reached the user's record (F11.1, BRD A12, A15).

    Kept on every receipt because a question about a wrong figure starts with
    where the data came from. Only PHOTO has an intake today; the rest arrive
    with E11's channels.
    """

    PHOTO = "photo"
    EMAIL = "email"
    QR = "qr"


class Receipt(Model):
    """One purchase transaction, arriving through an intake channel."""

    __tablename__ = "receipts"
    # Every month total, list and statistic filters one user's receipts by the
    # date they are filed under: printed date, else upload date (F7.1).
    __table_args__ = (
        Index(
            "ix_receipts_user_purchased",
            "user_id",
            text("coalesce(transaction_date, created_at)"),
        ),
        # A receipt arriving again is found by its fiscal identity (F11.5, ADR-0015).
        Index("ix_receipts_user_fiscal", "user_id", "fiscal_register_id", "fiscal_receipt_number"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    channel: Mapped[ReceiptChannel] = mapped_column(
        Enum(ReceiptChannel, name="receipt_channel_enum", create_type=False),
        default=ReceiptChannel.PHOTO,
        server_default=ReceiptChannel.PHOTO.name,
        nullable=False,
    )
    source_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # The register's number and this receipt's number on it, normalised (F11.3); both or
    # neither, and together unique to one real receipt.
    fiscal_register_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    fiscal_receipt_number: Mapped[str | None] = mapped_column(String(40), nullable=True)
    # Set on a receipt that arrived without the wizard and looks like an earlier one by
    # merchant, date and total, until the user keeps both or removes it (F11.5.2, A14).
    possible_duplicate_of_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("receipts.id", ondelete="SET NULL"), nullable=True
    )
    # Hidden from the owner's household, which still counts its money (F12.4, ADR-0017).
    is_private: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false"), nullable=False
    )
    merchant_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    transaction_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    total_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    # A receipt paid in another currency keeps what was printed and the rate it was
    # converted at; its amounts above are in the account's currency (F11.7, ADR-0016).
    # A currency with no rate means the amounts are still the printed ones, held in review.
    original_currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    original_total: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    exchange_rate: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    exchange_rate_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    exchange_rate_source: Mapped[str | None] = mapped_column(String(20), nullable=True)
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

    # `ordering_list` numbers the items as they are assigned, so the order the
    # receipt was printed in (or the user arranged it in) survives any later update.
    line_items: Mapped[list["LineItem"]] = relationship(
        "LineItem",
        back_populates="receipt",
        cascade="all, delete-orphan",
        order_by="LineItem.position",
        collection_class=ordering_list("position"),
    )
