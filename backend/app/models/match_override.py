import uuid

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Model


class PositionMatchOverride(Model):
    __tablename__ = "position_match_overrides"
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("upload_jobs.id", ondelete="CASCADE"), index=True
    )
    extraction_index: Mapped[int] = mapped_column()
    match_index: Mapped[int] = mapped_column()
    original_result: Mapped[str] = mapped_column()
    corrected_result: Mapped[str] = mapped_column()
