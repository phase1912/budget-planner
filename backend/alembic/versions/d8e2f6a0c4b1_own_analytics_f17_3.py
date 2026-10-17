"""What the service records about its own use (F17.3)

Revision ID: d8e2f6a0c4b1
Revises: c7d1e5a9b3f2
Create Date: 2026-10-17 14:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d8e2f6a0c4b1"
down_revision: str | Sequence[str] | None = "c7d1e5a9b3f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _base_columns() -> list[sa.Column]:  # type: ignore[type-arg]
    return [
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    ]


def upgrade() -> None:
    """Add-only (ADR-0014): two new tables the running code never reads."""
    op.create_table(
        "activity_events",
        *_base_columns(),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("event", sa.String(32), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_activity_events_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_activity_events")),
    )
    op.create_index(op.f("ix_activity_events_user_id"), "activity_events", ["user_id"])
    op.create_index(
        "ix_activity_events_event_created_at", "activity_events", ["event", "created_at"]
    )
    op.create_table(
        "page_view_counts",
        *_base_columns(),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("page", sa.String(32), nullable=False),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("views", sa.Integer(), nullable=False),
        sa.Column("entries", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_page_view_counts")),
        sa.UniqueConstraint("day", "page", "source", name="uq_page_view_counts_key"),
    )


def downgrade() -> None:
    op.drop_table("page_view_counts")
    op.drop_index("ix_activity_events_event_created_at", table_name="activity_events")
    op.drop_index(op.f("ix_activity_events_user_id"), table_name="activity_events")
    op.drop_table("activity_events")
