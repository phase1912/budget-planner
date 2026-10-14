"""Trips (F20.1)

Revision ID: b4e8c2a6d9f1
Revises: a7d3e9f1c5b8
Create Date: 2026-10-15 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b4e8c2a6d9f1"
down_revision: str | Sequence[str] | None = "a7d3e9f1c5b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add-only (ADR-0014): a new table and two columns receipts default to "no trip"."""
    op.create_table(
        "trips",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum("personal", "business", name="trip_kind", native_enum=False, length=16),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("country", sa.String(length=2), nullable=True),
        sa.Column("city", sa.String(length=120), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("purpose", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_trips_user_id", "trips", ["user_id"])
    op.add_column("receipts", sa.Column("trip_id", sa.Uuid(), nullable=True))
    op.add_column(
        "receipts",
        sa.Column("trip_manual", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.create_foreign_key(
        "fk_receipts_trip_id", "receipts", "trips", ["trip_id"], ["id"], ondelete="SET NULL"
    )
    op.create_index("ix_receipts_trip_id", "receipts", ["trip_id"])


def downgrade() -> None:
    """Remove trips and the receipts' links to them."""
    op.drop_index("ix_receipts_trip_id", table_name="receipts")
    op.drop_constraint("fk_receipts_trip_id", "receipts", type_="foreignkey")
    op.drop_column("receipts", "trip_manual")
    op.drop_column("receipts", "trip_id")
    op.drop_index("ix_trips_user_id", table_name="trips")
    op.drop_table("trips")
