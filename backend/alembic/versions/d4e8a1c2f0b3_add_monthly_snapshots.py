"""Add monthly_snapshots for finalised months (F6.4, BRD D5)

Revision ID: d4e8a1c2f0b3
Revises: b81cae0ce01f
Create Date: 2026-09-26 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "d4e8a1c2f0b3"
down_revision: str | Sequence[str] | None = "b81cae0ce01f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the snapshots table, one row per user and calendar month."""
    op.create_table(
        "monthly_snapshots",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("month", sa.Integer(), nullable=False),
        sa.Column("total", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("receipt_count", sa.Integer(), nullable=False),
        sa.Column("excluded_count", sa.Integer(), nullable=False),
        sa.Column("excluded_amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_monthly_snapshots_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_monthly_snapshots")),
        sa.UniqueConstraint("user_id", "year", "month", name="uq_monthly_snapshot_month"),
    )
    op.create_index(
        op.f("ix_monthly_snapshots_user_id"), "monthly_snapshots", ["user_id"], unique=False
    )


def downgrade() -> None:
    """Drop the snapshots table."""
    op.drop_index(op.f("ix_monthly_snapshots_user_id"), table_name="monthly_snapshots")
    op.drop_table("monthly_snapshots")
