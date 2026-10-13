"""Line read confidence (F15.2)

Revision ID: c3a7e2d41f90
Revises: 31658f5fedb1
Create Date: 2026-10-13 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3a7e2d41f90"
down_revision: str | Sequence[str] | None = "31658f5fedb1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add-only, nullable (ADR-0014): lines stored before it have no score and no mark."""
    op.add_column("line_items", sa.Column("read_confidence", sa.Integer(), nullable=True))


def downgrade() -> None:
    """Remove the read confidence."""
    op.drop_column("line_items", "read_confidence")
