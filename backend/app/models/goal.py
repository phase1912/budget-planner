import enum
import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Boolean, Date, Enum, ForeignKey, Numeric, String, Text, false
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.domain.goals import FinancialKind, GoalType
from app.models.base import Model


def _as_text(kind: type[enum.StrEnum], name: str) -> Enum:
    """Short text rather than a PostgreSQL enum type, so a new value needs no migration."""
    return Enum(
        kind,
        name=name,
        native_enum=False,
        length=32,
        values_callable=lambda members: [m.value for m in members],
    )


class Goal(Model):
    """A financial or lifestyle objective the user declared (BRD F1 — F8.1).

    A financial goal has a `financial_kind` and a `target_amount`, plus a
    `category_id` when it cuts one category; a lifestyle goal has neither, only its
    words, which F8.2 translates into the spending lines it watches
    (`mapped_category_ids`, `mapped_item_names`, F9). Once the user corrects that
    list, `mapping_set_by_user` keeps later automatic passes off it. The rules that
    keep these consistent live in `app.domain.goals`.
    """

    __tablename__ = "goals"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type: Mapped[GoalType] = mapped_column(_as_text(GoalType, "goal_type"), nullable=False)
    financial_kind: Mapped[FinancialKind | None] = mapped_column(
        _as_text(FinancialKind, "financial_kind"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    # A deleted category leaves the goal without one rather than taking the goal with it.
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )
    mapped_category_ids: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(Uuid(as_uuid=True)), server_default="{}", nullable=False
    )
    mapped_item_names: Mapped[list[str]] = mapped_column(
        ARRAY(String(120)), server_default="{}", nullable=False
    )
    mapping_set_by_user: Mapped[bool] = mapped_column(
        Boolean, server_default=false(), nullable=False
    )
    # The 1st of the month the user dismissed this goal's at-risk warning for (F8.8).
    warning_dismissed_for: Mapped[date | None] = mapped_column(Date, nullable=True)
