"""Data rights: deleting an account takes everything; accepted terms are recorded (F17.9)

Revision ID: c7d1e5a9b3f2
Revises: b4e8c2d6f1a3
Create Date: 2026-10-17 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c7d1e5a9b3f2"
down_revision: str | Sequence[str] | None = "b4e8c2d6f1a3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_FK = "fk_upload_jobs_user_id_users"


def upgrade() -> None:
    """Add-only (ADR-0014). Upload jobs were the only user reference without ON DELETE;
    the running code never deletes users. Terms are unknown for accounts opened before."""
    op.drop_constraint(_FK, "upload_jobs", type_="foreignkey")
    op.create_foreign_key(_FK, "upload_jobs", "users", ["user_id"], ["id"], ondelete="CASCADE")
    op.add_column("users", sa.Column("terms_accepted_at", sa.DateTime(timezone=True)))
    op.add_column("users", sa.Column("terms_version", sa.String(20)))


def downgrade() -> None:
    op.drop_column("users", "terms_version")
    op.drop_column("users", "terms_accepted_at")
    op.drop_constraint(_FK, "upload_jobs", type_="foreignkey")
    op.create_foreign_key(_FK, "upload_jobs", "users", ["user_id"], ["id"])
