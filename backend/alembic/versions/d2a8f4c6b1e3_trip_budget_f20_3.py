"""Trip budget (F20.3)

Revision ID: d2a8f4c6b1e3
Revises: c5f1a7d3e2b9
Create Date: 2026-10-15 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d2a8f4c6b1e3"
down_revision: str | Sequence[str] | None = "c5f1a7d3e2b9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add-only (ADR-0014): an empty column; a trip recorded before it has no budget."""
    op.add_column("trips", sa.Column("budget", sa.Numeric(12, 2), nullable=True))


def downgrade() -> None:
    op.drop_column("trips", "budget")
