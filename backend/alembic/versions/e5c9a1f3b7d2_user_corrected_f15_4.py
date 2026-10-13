"""User-corrected receipts and lines (F15.4)

Revision ID: e5c9a1f3b7d2
Revises: d81f4b6a2c07
Create Date: 2026-10-13 21:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e5c9a1f3b7d2"
down_revision: str | Sequence[str] | None = "d81f4b6a2c07"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add-only (ADR-0014): receipts stored before it count as never corrected."""
    op.add_column(
        "receipts",
        sa.Column("user_corrected", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.add_column(
        "line_items",
        sa.Column("user_corrected", sa.Boolean(), server_default=sa.false(), nullable=False),
    )


def downgrade() -> None:
    """Remove the marks."""
    op.drop_column("line_items", "user_corrected")
    op.drop_column("receipts", "user_corrected")
