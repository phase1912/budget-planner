"""Add recommendations (F8.4, BRD F3)

One row per piece of advice on a goal: the category or recurring purchase it
targets, what to do and why. The target kind is short text rather than a
PostgreSQL enum type, like the goal's, so a downgrade leaves nothing behind.

Revision ID: 520d3533795d
Revises: 8ac772d1e353
Create Date: 2026-09-30 14:25:37.811569

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "520d3533795d"
down_revision: str | Sequence[str] | None = "8ac772d1e353"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the recommendations table, indexed by owner and by goal."""
    op.create_table(
        "recommendations",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("goal_id", sa.Uuid(), nullable=False),
        sa.Column(
            "target_kind",
            sa.Enum("category", "item", name="advice_target", native_enum=False, length=16),
            nullable=False,
        ),
        sa.Column("target_name", sa.String(length=255), nullable=False),
        sa.Column("action", sa.String(length=255), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["goal_id"],
            ["goals.id"],
            name=op.f("fk_recommendations_goal_id_goals"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_recommendations_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_recommendations")),
    )
    op.create_index(op.f("ix_recommendations_goal_id"), "recommendations", ["goal_id"])
    op.create_index(op.f("ix_recommendations_user_id"), "recommendations", ["user_id"])


def downgrade() -> None:
    """Drop it again."""
    op.drop_index(op.f("ix_recommendations_user_id"), table_name="recommendations")
    op.drop_index(op.f("ix_recommendations_goal_id"), table_name="recommendations")
    op.drop_table("recommendations")
