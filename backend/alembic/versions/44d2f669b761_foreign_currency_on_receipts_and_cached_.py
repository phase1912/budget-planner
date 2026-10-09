"""Foreign currency on receipts and cached exchange rates (F11.7)

Revision ID: 44d2f669b761
Revises: f3a9c2d18e47
Create Date: 2026-10-09 18:59:51.995173

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "44d2f669b761"
down_revision: str | Sequence[str] | None = "f3a9c2d18e47"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add-only, so the code already running is unaffected (ADR-0014)."""
    op.create_table(
        "exchange_rates",
        sa.Column("base", sa.String(length=3), nullable=False),
        sa.Column("quote", sa.String(length=3), nullable=False),
        sa.Column("requested_date", sa.Date(), nullable=False),
        sa.Column("rate", sa.Numeric(precision=18, scale=8), nullable=False),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_exchange_rates")),
        sa.UniqueConstraint("base", "quote", "requested_date", name=op.f("uq_exchange_rates_base")),
    )
    op.add_column("receipts", sa.Column("original_currency", sa.String(length=3), nullable=True))
    op.add_column(
        "receipts", sa.Column("original_total", sa.Numeric(precision=12, scale=2), nullable=True)
    )
    op.add_column(
        "receipts", sa.Column("exchange_rate", sa.Numeric(precision=18, scale=8), nullable=True)
    )
    op.add_column("receipts", sa.Column("exchange_rate_date", sa.Date(), nullable=True))
    op.add_column(
        "receipts", sa.Column("exchange_rate_source", sa.String(length=20), nullable=True)
    )


def downgrade() -> None:
    """Remove the columns and the cache."""
    op.drop_column("receipts", "exchange_rate_source")
    op.drop_column("receipts", "exchange_rate_date")
    op.drop_column("receipts", "exchange_rate")
    op.drop_column("receipts", "original_total")
    op.drop_column("receipts", "original_currency")
    op.drop_table("exchange_rates")
