import uuid

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Model


class NameCorrection(Model):
    """A line name the user corrected, remembered for that shop's later receipts (F15.3).

    Created when the owner renames a line on a receipt from a known merchant; later
    receipts from that merchant read the same printed name as `corrected_name`. The
    merchant and the printed name are stored normalised
    (`app.domain.categories.normalise_name`), so one correction exists per user,
    merchant and printed name, and the latest one wins.
    """

    __tablename__ = "name_corrections"
    __table_args__ = (
        UniqueConstraint("user_id", "merchant_name", "read_name", name="uq_name_correction"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    merchant_name: Mapped[str] = mapped_column(String(255), nullable=False)
    read_name: Mapped[str] = mapped_column(String(255), nullable=False)
    corrected_name: Mapped[str] = mapped_column(String(255), nullable=False)
