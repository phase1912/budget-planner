"""Remember when the user corrected what a goal watches (F8.2, BRD F9)

A lifestyle goal's spending lines are first chosen by the model; once the user
corrects them, later automatic passes must leave them alone. Existing goals have
never been corrected, so they start false.

Revision ID: 8ac772d1e353
Revises: 5de37b08c136
Create Date: 2026-09-29 16:47:19.355669

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "8ac772d1e353"
down_revision: str | Sequence[str] | None = "5de37b08c136"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add the flag, false for every goal so far."""
    op.add_column(
        "goals",
        sa.Column(
            "mapping_set_by_user", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
    )


def downgrade() -> None:
    """Drop it again."""
    op.drop_column("goals", "mapping_set_by_user")
