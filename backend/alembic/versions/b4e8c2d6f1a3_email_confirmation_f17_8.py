"""Email confirmation on accounts (F17.8.2)

Revision ID: b4e8c2d6f1a3
Revises: a3d5f7b9c1e2
Create Date: 2026-10-16 18:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b4e8c2d6f1a3"
down_revision: str | Sequence[str] | None = "a3d5f7b9c1e2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add-only (ADR-0014). Accounts that existed before confirmation are trusted as they are."""
    op.add_column(
        "users", sa.Column("email_confirmed_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.execute("UPDATE users SET email_confirmed_at = now()")


def downgrade() -> None:
    op.drop_column("users", "email_confirmed_at")
