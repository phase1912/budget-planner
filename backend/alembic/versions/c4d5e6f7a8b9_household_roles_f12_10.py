"""household roles f12 10

Revision ID: c4d5e6f7a8b9
Revises: b7c1d2e3f4a5
Create Date: 2026-10-19 20:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c4d5e6f7a8b9"
down_revision: str | Sequence[str] | None = "b7c1d2e3f4a5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema: the owner may keep the household budget to themselves (add-only)."""
    op.add_column(
        "households",
        sa.Column("owner_sets_budget", sa.Boolean(), server_default=sa.false(), nullable=False),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("households", "owner_sets_budget")
