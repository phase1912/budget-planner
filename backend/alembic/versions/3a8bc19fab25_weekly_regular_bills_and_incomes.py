"""Weekly regular bills and incomes (F23.21): a weekday beside the monthly day.

Add-only: null keeps every existing rule monthly, as the running code reads it.

Revision ID: 3a8bc19fab25
Revises: 1967459b0aff
Create Date: 2026-10-20 19:08:26.495309

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3a8bc19fab25"
down_revision: str | Sequence[str] | None = "1967459b0aff"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("income_sources", sa.Column("weekday", sa.SmallInteger(), nullable=True))
    op.add_column("regular_expenses", sa.Column("weekday", sa.SmallInteger(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("regular_expenses", "weekday")
    op.drop_column("income_sources", "weekday")
