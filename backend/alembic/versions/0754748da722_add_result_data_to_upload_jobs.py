"""Add result_data column to upload_jobs

Revision ID: 0754748da722
Revises: 90a2497c4c2f
Create Date: 2026-08-26 19:23:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0754748da722"
down_revision: str | None = "90a2497c4c2f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("upload_jobs", sa.Column("result_data", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("upload_jobs", "result_data")
