"""Asking before data goes to the AI (F25.3.2)

Revision ID: b13d61a3cac3
Revises: b7e2c4d6f8a1
Create Date: 2026-10-23 20:23:22.960208

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b13d61a3cac3"
down_revision: str | Sequence[str] | None = "b7e2c4d6f8a1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add-only (ADR-0014): a column the running code never reads. Nobody has allowed it
    yet: every account is asked, existing ones included, before its next AI call."""
    op.add_column("users", sa.Column("ai_consent_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "ai_consent_at")
