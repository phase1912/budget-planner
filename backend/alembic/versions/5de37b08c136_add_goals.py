"""Add goals (F8.1, BRD F1)

One row per goal a user states: financial ones with their kind, amount and, when
they cut one, a category; lifestyle ones with the spending lines F8.2 maps them to.
Types and kinds are stored as short text rather than PostgreSQL enum types, so a
downgrade leaves nothing behind and a new kind needs no migration.

Revision ID: 5de37b08c136
Revises: 1e0496d719c2
Create Date: 2026-09-28 20:03:56.854979

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "5de37b08c136"
down_revision: str | Sequence[str] | None = "1e0496d719c2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the goals table, indexed by owner."""
    op.create_table(
        "goals",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "type",
            sa.Enum("financial", "lifestyle", name="goal_type", native_enum=False, length=32),
            nullable=False,
        ),
        sa.Column(
            "financial_kind",
            sa.Enum(
                "spending_ceiling",
                "savings_target",
                "category_reduction",
                name="financial_kind",
                native_enum=False,
                length=32,
            ),
            nullable=True,
        ),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("target_amount", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("category_id", sa.Uuid(), nullable=True),
        sa.Column(
            "mapped_category_ids", postgresql.ARRAY(sa.Uuid()), server_default="{}", nullable=False
        ),
        sa.Column(
            "mapped_item_names",
            postgresql.ARRAY(sa.String(length=120)),
            server_default="{}",
            nullable=False,
        ),
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
            ["category_id"],
            ["categories.id"],
            name=op.f("fk_goals_category_id_categories"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_goals_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_goals")),
    )
    op.create_index(op.f("ix_goals_user_id"), "goals", ["user_id"], unique=False)


def downgrade() -> None:
    """Drop it again."""
    op.drop_index(op.f("ix_goals_user_id"), table_name="goals")
    op.drop_table("goals")
