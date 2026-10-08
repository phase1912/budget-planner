"""Give every user a receipt forwarding token (F11.2)

Revision ID: d17102912dfc
Revises: 336ba6a8c5c4
Create Date: 2026-10-08 18:38:36.260618

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d17102912dfc"
down_revision: str | Sequence[str] | None = "336ba6a8c5c4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add the column, give existing users a random token, then require one."""
    op.add_column("users", sa.Column("forwarding_token", sa.String(length=32), nullable=True))
    op.execute("UPDATE users SET forwarding_token = substr(md5(random()::text || id::text), 1, 16)")
    op.alter_column("users", "forwarding_token", nullable=False)
    op.create_unique_constraint("uq_users_forwarding_token", "users", ["forwarding_token"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("uq_users_forwarding_token", "users", type_="unique")
    op.drop_column("users", "forwarding_token")
