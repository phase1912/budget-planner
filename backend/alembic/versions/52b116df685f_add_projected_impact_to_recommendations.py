"""Add what following a recommendation is worth (F8.5, BRD F4)

Each recommendation now carries the share of its target's spending it removes, the
monthly saving and, for a recurring purchase, the purchases avoided a month — all
worked out from the receipts. Advice stored before has none of these and no honest
value to fill in, so it is dropped: it is derived data, asked for again in one click.

Revision ID: 52b116df685f
Revises: 520d3533795d
Create Date: 2026-10-01 15:16:20.198493

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "52b116df685f"
down_revision: str | Sequence[str] | None = "520d3533795d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Drop advice without an impact, then add the impact columns."""
    op.execute("DELETE FROM recommendations")
    op.add_column("recommendations", sa.Column("reduction_percent", sa.Integer(), nullable=False))
    op.add_column(
        "recommendations",
        sa.Column("monthly_saving", sa.Numeric(precision=12, scale=2), nullable=False),
    )
    op.add_column(
        "recommendations",
        sa.Column("purchases_avoided", sa.Numeric(precision=8, scale=1), nullable=True),
    )


def downgrade() -> None:
    """Drop the impact columns again; the advice itself is kept."""
    op.drop_column("recommendations", "purchases_avoided")
    op.drop_column("recommendations", "monthly_saving")
    op.drop_column("recommendations", "reduction_percent")
