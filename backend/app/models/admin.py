"""What admins grant and do (F18.6)."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Model


class PlanGrant(Model):
    """A plan an admin gave an account for a time (F18.6.3); the running one sets its plan.

    Owned by the account, so it is exported and deleted with it. A grant taken back keeps
    its row with `revoked_at`, so the history stays readable in the admin log.
    """

    __tablename__ = "plan_grants"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    plan: Mapped[str] = mapped_column(String(16), nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reason: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    granted_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AdminAction(Model):
    """One thing an admin did to an account, for the log super admins read (F18.6.3).

    Neither side owns it: deleting either account leaves the entry, with that side gone.
    """

    __tablename__ = "admin_actions"

    admin_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    target_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    action: Mapped[str] = mapped_column(String(40), nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
