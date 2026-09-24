import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Model

if TYPE_CHECKING:
    from app.models.category import Category


class CategoryRule(Model):
    """A user's correction, remembered for future items (BRD C5, ADR-0008).

    Created when the owner reassigns an item with "apply to future items". It
    files later items from the same merchant with the same or a highly similar
    name under the chosen category, ahead of the categoriser. Names are stored
    normalised (`app.domain.categories.normalise_name`), so one rule exists per
    user, merchant and item name.
    """

    __tablename__ = "category_rules"
    __table_args__ = (
        UniqueConstraint("user_id", "merchant_name", "item_name", name="uq_category_rule_item"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    merchant_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    item_name: Mapped[str] = mapped_column(String(255), nullable=False)
    category_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("categories.id", ondelete="CASCADE"), nullable=False
    )

    category: Mapped["Category"] = relationship("Category")
