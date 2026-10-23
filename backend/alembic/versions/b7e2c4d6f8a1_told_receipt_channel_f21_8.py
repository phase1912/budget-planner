"""Receipts told in the chat (F21.8.1)

Revision ID: b7e2c4d6f8a1
Revises: 2aa64bbe5306
Create Date: 2026-10-23 18:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7e2c4d6f8a1"
down_revision: str | Sequence[str] | None = "2aa64bbe5306"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add-only (ADR-0014): one more channel the running code never writes."""
    op.execute("ALTER TYPE receipt_channel_enum ADD VALUE IF NOT EXISTS 'TOLD'")


def downgrade() -> None:
    # PostgreSQL cannot drop one enum label, so the type is rebuilt. A receipt told in the
    # chat reads as one typed in by hand afterwards, the nearest channel left.
    op.execute("UPDATE receipts SET channel = 'MANUAL' WHERE channel = 'TOLD'")
    op.execute("UPDATE upload_jobs SET channel = 'MANUAL' WHERE channel = 'TOLD'")
    op.execute("ALTER TABLE receipts ALTER COLUMN channel DROP DEFAULT")
    op.execute("ALTER TABLE upload_jobs ALTER COLUMN channel DROP DEFAULT")
    op.execute("ALTER TYPE receipt_channel_enum RENAME TO receipt_channel_enum_old")
    op.execute("CREATE TYPE receipt_channel_enum AS ENUM ('PHOTO', 'EMAIL', 'QR', 'MANUAL')")
    for table in ("receipts", "upload_jobs"):
        op.execute(
            f"ALTER TABLE {table} ALTER COLUMN channel TYPE receipt_channel_enum "
            "USING channel::text::receipt_channel_enum"
        )
        op.execute(f"ALTER TABLE {table} ALTER COLUMN channel SET DEFAULT 'PHOTO'")
    op.execute("DROP TYPE receipt_channel_enum_old")
