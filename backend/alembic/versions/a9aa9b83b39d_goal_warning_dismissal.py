"""Remember the month a goal's at-risk warning was dismissed (F8.8, BRD F7)

A warning that a goal is heading over its cap is worked out live from the month's
pace; only the user's "not now" is stored, as the first day of the month it holds
for, so the warning returns on its own next month.

Revision ID: a9aa9b83b39d
Revises: 52b116df685f
Create Date: 2026-10-06 11:30:16.991082

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a9aa9b83b39d"
down_revision: str | Sequence[str] | None = "52b116df685f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add the dismissal month, empty for every goal so far."""
    op.add_column("goals", sa.Column("warning_dismissed_for", sa.Date(), nullable=True))


def downgrade() -> None:
    """Drop it again."""
    op.drop_column("goals", "warning_dismissed_for")
