"""Business trip advance (F20.5)

Revision ID: f1c6e8b4a7d2
Revises: e7b3d9a5c2f4
Create Date: 2026-10-15 18:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f1c6e8b4a7d2"
down_revision: str | Sequence[str] | None = "e7b3d9a5c2f4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add-only (ADR-0014): empty columns; a trip recorded before them had no advance."""
    op.add_column("trips", sa.Column("advance", sa.Numeric(12, 2), nullable=True))
    op.add_column("trips", sa.Column("advance_paid_on", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("trips", "advance_paid_on")
    op.drop_column("trips", "advance")
