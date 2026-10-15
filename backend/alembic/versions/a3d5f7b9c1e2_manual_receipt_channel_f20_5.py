"""Expenses typed in without a receipt (F20.5)

Revision ID: a3d5f7b9c1e2
Revises: f1c6e8b4a7d2
Create Date: 2026-10-15 19:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a3d5f7b9c1e2"
down_revision: str | Sequence[str] | None = "f1c6e8b4a7d2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add-only (ADR-0014): one more channel the running code never writes."""
    op.execute("ALTER TYPE receipt_channel_enum ADD VALUE IF NOT EXISTS 'MANUAL'")


def downgrade() -> None:
    # PostgreSQL cannot drop one enum label, so the type is rebuilt. An expense typed in
    # by hand reads as a photo receipt afterwards, the nearest channel left.
    op.execute("UPDATE receipts SET channel = 'PHOTO' WHERE channel = 'MANUAL'")
    op.execute("UPDATE upload_jobs SET channel = 'PHOTO' WHERE channel = 'MANUAL'")
    op.execute("ALTER TABLE receipts ALTER COLUMN channel DROP DEFAULT")
    op.execute("ALTER TABLE upload_jobs ALTER COLUMN channel DROP DEFAULT")
    op.execute("ALTER TYPE receipt_channel_enum RENAME TO receipt_channel_enum_old")
    op.execute("CREATE TYPE receipt_channel_enum AS ENUM ('PHOTO', 'EMAIL', 'QR')")
    for table in ("receipts", "upload_jobs"):
        op.execute(
            f"ALTER TABLE {table} ALTER COLUMN channel TYPE receipt_channel_enum "
            "USING channel::text::receipt_channel_enum"
        )
        op.execute(f"ALTER TABLE {table} ALTER COLUMN channel SET DEFAULT 'PHOTO'")
    op.execute("DROP TYPE receipt_channel_enum_old")
