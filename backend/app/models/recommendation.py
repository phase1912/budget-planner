import uuid
from decimal import Decimal

from sqlalchemy import Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.advice import ACTION_MAX_LENGTH, TARGET_MAX_LENGTH, AdviceTarget
from app.domain.goal_analysis import FeedbackState
from app.models.base import Model


class Recommendation(Model):
    """One piece of advice on one goal, citing the user's own receipts (BRD F3 — F8.4).

    `target_kind` and `target_name` say which category or recurring purchase it is
    about; `action` is what to do and `rationale` why, with the figures behind it.
    `monthly_saving` and `purchases_avoided` are what following it is worth, worked
    out from the receipts (`app.domain.advice.project_impact`, F8.5). Asking for
    advice on a goal again replaces its recommendations.
    """

    __tablename__ = "recommendations"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    goal_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("goals.id", ondelete="CASCADE"), nullable=False, index=True
    )
    target_kind: Mapped[AdviceTarget] = mapped_column(
        Enum(
            AdviceTarget,
            name="advice_target",
            native_enum=False,
            length=16,
            values_callable=lambda members: [m.value for m in members],
        ),
        nullable=False,
    )
    target_name: Mapped[str] = mapped_column(String(TARGET_MAX_LENGTH), nullable=False)
    action: Mapped[str] = mapped_column(String(ACTION_MAX_LENGTH), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    reduction_percent: Mapped[int] = mapped_column(Integer, nullable=False)
    monthly_saving: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    purchases_avoided: Mapped[Decimal | None] = mapped_column(Numeric(8, 1), nullable=True)
    feedback: Mapped[FeedbackState | None] = mapped_column(
        Enum(
            FeedbackState,
            name="feedback_state",
            native_enum=False,
            length=16,
            values_callable=lambda members: [m.value for m in members],
        ),
        nullable=True,
    )
