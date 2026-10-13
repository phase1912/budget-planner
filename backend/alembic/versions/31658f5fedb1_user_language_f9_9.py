"""User language (F9.9)

Revision ID: 31658f5fedb1
Revises: 8fc0335523eb
Create Date: 2026-10-12 19:44:00.605254

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "31658f5fedb1"
down_revision: str | Sequence[str] | None = "8fc0335523eb"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add-only, nullable (ADR-0014)."""
    op.add_column("users", sa.Column("language", sa.String(length=2), nullable=True))


def downgrade() -> None:
    """Remove the language."""
    op.drop_column("users", "language")
