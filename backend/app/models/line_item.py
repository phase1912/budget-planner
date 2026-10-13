import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Model

if TYPE_CHECKING:
    from app.models.category import Category
    from app.models.receipt import Receipt


class LineItem(Model):
    """One position on a receipt: product, quantity, unit price, total."""

    __tablename__ = "line_items"

    receipt_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("receipts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    total_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )
    category_confidence: Mapped[int | None] = mapped_column(Integer, nullable=True)
    read_confidence: Mapped[int | None] = mapped_column(Integer, nullable=True)
    """The reader's 0-100 score for this line (BRD A10); None once the user corrects it."""
    read_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    """What was printed, when the name shown is a remembered correction of it (F15.3)."""
    user_corrected: Mapped[bool] = mapped_column(default=False, server_default="false")
    """The user changed or added this line after it was read (F15.4)."""
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("products.id", ondelete="SET NULL"), nullable=True, index=True
    )
    """The product this line is a purchase of, once matched (F16.1)."""
    is_category_manual: Mapped[bool] = mapped_column(default=False, server_default="false")
    position: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    receipt: Mapped["Receipt"] = relationship("Receipt", back_populates="line_items")
    category: Mapped["Category"] = relationship("Category", lazy="joined", innerjoin=False)
