"""Merge multiple heads

Revision ID: edf81b4a2774
Revises: c7dfee8c1b06, f67084582974
Create Date: 2026-09-20 17:32:16.875247

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "edf81b4a2774"
down_revision: str | Sequence[str] | None = ("c7dfee8c1b06", "f67084582974")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
