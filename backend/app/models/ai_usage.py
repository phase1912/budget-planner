import uuid
from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Index, Integer, Numeric, String, true
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Model


class AiUsage(Model):
    """One model call and what it cost (F21.9.1, ADR-0030).

    `credits` is the cost at the model's own price, one credit to 0.001 USD; it counts
    against `user_id`'s monthly wallet only when `charged`. Calls nobody asked for, and
    calls outside a user, are kept with `charged` false: the bill is read from these rows.
    Removed with the account, like everything of the user's.
    """

    __tablename__ = "ai_usage"
    # A month's spend is summed per user and per day across users: both by time.
    __table_args__ = (
        Index("ix_ai_usage_user_id_created_at", "user_id", "created_at"),
        Index("ix_ai_usage_created_at", "created_at"),
    )

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    purpose: Mapped[str] = mapped_column(String(32), nullable=False)
    model: Mapped[str] = mapped_column(String(120), nullable=False)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    audio_seconds: Mapped[Decimal] = mapped_column(
        Numeric(8, 2), nullable=False, server_default="0"
    )
    credits: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    charged: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=true())
