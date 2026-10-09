"""Record the intake channel on upload jobs (F11.1.4)

Revision ID: e2c4a1f07b3d
Revises: d17102912dfc
Create Date: 2026-10-09 09:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e2c4a1f07b3d"
down_revision: str | Sequence[str] | None = "d17102912dfc"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Every existing job came through the photo upload, the only channel with a job."""
    channel = postgresql.ENUM(name="receipt_channel_enum", create_type=False)
    op.add_column(
        "upload_jobs",
        sa.Column("channel", channel, nullable=False, server_default="PHOTO"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("upload_jobs", "channel")
