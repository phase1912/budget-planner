"""Business trip times for the per diem (F20.4)

Revision ID: e7b3d9a5c2f4
Revises: d2a8f4c6b1e3
Create Date: 2026-10-15 16:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e7b3d9a5c2f4"
down_revision: str | Sequence[str] | None = "d2a8f4c6b1e3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TIMES = ("departed_at", "returned_at", "abroad_from", "abroad_to")


def upgrade() -> None:
    """Add-only (ADR-0014): empty columns; a trip recorded before them has no per diem."""
    for column in TIMES:
        op.add_column("trips", sa.Column(column, sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "trips", sa.Column("meals_provided", postgresql.JSONB(astext_type=sa.Text()), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("trips", "meals_provided")
    for column in reversed(TIMES):
        op.drop_column("trips", column)
