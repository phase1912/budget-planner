"""Private receipts (F12.4)

Revision ID: 483802ab337c
Revises: e55ec1c71eab
Create Date: 2026-10-09 20:42:50.527784

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "483802ab337c"
down_revision: str | Sequence[str] | None = "e55ec1c71eab"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add-only, with a default the running code never has to set (ADR-0014)."""
    op.add_column(
        "receipts",
        sa.Column("is_private", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )


def downgrade() -> None:
    """Remove the private mark."""
    op.drop_column("receipts", "is_private")
