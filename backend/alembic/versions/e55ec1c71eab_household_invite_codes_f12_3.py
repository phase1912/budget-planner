"""Household invite codes (F12.3)

Revision ID: e55ec1c71eab
Revises: 88a4bf63159b
Create Date: 2026-10-09 19:55:49.110758

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e55ec1c71eab"
down_revision: str | Sequence[str] | None = "88a4bf63159b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add-only; the server default gives any existing household a code (ADR-0014)."""
    op.add_column(
        "households",
        sa.Column(
            "invite_code",
            sa.String(length=32),
            server_default=sa.text("replace((gen_random_uuid())::text, '-'::text, ''::text)"),
            nullable=False,
        ),
    )
    op.create_unique_constraint(op.f("uq_households_invite_code"), "households", ["invite_code"])


def downgrade() -> None:
    """Remove the invite codes."""
    op.drop_constraint(op.f("uq_households_invite_code"), "households", type_="unique")
    op.drop_column("households", "invite_code")
