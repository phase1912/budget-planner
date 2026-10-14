import uuid

from sqlalchemy import ForeignKey, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Model


class ProductSelection(Model):
    """Products the user explores together, saved under a name ("Snacks") (F16.2).

    `product_ids` follow merges and splits (F16.1), so the selection keeps meaning what the
    user picked. Per user (N2).
    """

    __tablename__ = "product_selections"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(60), nullable=False)
    product_ids: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb")
    )
