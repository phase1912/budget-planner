"""Household budget limit (F12.5)

Revision ID: 8fc0335523eb
Revises: 483802ab337c
Create Date: 2026-10-10 18:02:12.510007

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8fc0335523eb"
down_revision: str | Sequence[str] | None = "483802ab337c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add-only, nullable (ADR-0014)."""
    op.add_column(
        "households", sa.Column("budget_limit", sa.Numeric(precision=12, scale=2), nullable=True)
    )


def downgrade() -> None:
    """Remove the household budget."""
    op.drop_column("households", "budget_limit")
