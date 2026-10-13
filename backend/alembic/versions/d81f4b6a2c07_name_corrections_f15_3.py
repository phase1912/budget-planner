"""Name corrections (F15.3)

Revision ID: d81f4b6a2c07
Revises: c3a7e2d41f90
Create Date: 2026-10-13 18:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d81f4b6a2c07"
down_revision: str | Sequence[str] | None = "c3a7e2d41f90"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add-only (ADR-0014): a new table and a nullable column."""
    op.create_table(
        "name_corrections",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("merchant_name", sa.String(length=255), nullable=False),
        sa.Column("read_name", sa.String(length=255), nullable=False),
        sa.Column("corrected_name", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "merchant_name", "read_name", name="uq_name_correction"),
    )
    op.create_index("ix_name_corrections_user_id", "name_corrections", ["user_id"])
    op.add_column("line_items", sa.Column("read_name", sa.String(length=255), nullable=True))


def downgrade() -> None:
    """Remove the corrections and what was printed."""
    op.drop_column("line_items", "read_name")
    op.drop_index("ix_name_corrections_user_id", table_name="name_corrections")
    op.drop_table("name_corrections")
