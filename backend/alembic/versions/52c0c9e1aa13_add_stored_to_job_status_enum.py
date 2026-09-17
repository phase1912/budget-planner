"""add STORED to job_status_enum

The ``JobStatus.STORED`` state exists in the model and is written when an upload
job's extractions are committed, but the enum type was created without it, so
that write failed against a real database.

Revision ID: 52c0c9e1aa13
Revises: 20c1eae2b0d4
Create Date: 2026-09-17 19:41:14.958055

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "52c0c9e1aa13"
down_revision: str | Sequence[str] | None = "20c1eae2b0d4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TYPE job_status_enum ADD VALUE IF NOT EXISTS 'STORED' BEFORE 'FAILED'")


def downgrade() -> None:
    """Downgrade schema."""
    # PostgreSQL cannot drop a single enum label, so the type is rebuilt. Jobs
    # already committed are reported as COMPLETED, the nearest surviving state.
    op.execute("UPDATE upload_jobs SET status = 'COMPLETED' WHERE status = 'STORED'")
    op.execute("ALTER TYPE job_status_enum RENAME TO job_status_enum_old")
    op.execute(
        "CREATE TYPE job_status_enum AS ENUM ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED')"
    )
    op.execute(
        "ALTER TABLE upload_jobs ALTER COLUMN status TYPE job_status_enum "
        "USING status::text::job_status_enum"
    )
    op.execute("DROP TYPE job_status_enum_old")
