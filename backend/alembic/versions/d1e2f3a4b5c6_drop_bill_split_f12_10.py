"""drop the split of a shared bill f12 10

Revision ID: d1e2f3a4b5c6
Revises: 12b7f85c9506
Create Date: 2026-10-19 21:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d1e2f3a4b5c6"
down_revision: str | Sequence[str] | None = "12b7f85c9506"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema: a shared bill is never divided (ADR-0023); the code that read
    `split` stopped in the merge before this one (ADR-0014)."""
    op.drop_column("regular_expenses", "split")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column("regular_expenses", sa.Column("split", sa.String(length=8), nullable=True))
