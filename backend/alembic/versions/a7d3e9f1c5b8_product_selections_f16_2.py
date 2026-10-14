"""Saved product selections (F16.2)

Revision ID: a7d3e9f1c5b8
Revises: f2a8c4d6e1b3
Create Date: 2026-10-15 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a7d3e9f1c5b8"
down_revision: str | Sequence[str] | None = "f2a8c4d6e1b3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add-only (ADR-0014): a new table."""
    op.create_table(
        "product_selections",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=60), nullable=False),
        sa.Column("product_ids", JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_product_selections_user_id", "product_selections", ["user_id"])


def downgrade() -> None:
    """Remove the saved selections."""
    op.drop_index("ix_product_selections_user_id", table_name="product_selections")
    op.drop_table("product_selections")
