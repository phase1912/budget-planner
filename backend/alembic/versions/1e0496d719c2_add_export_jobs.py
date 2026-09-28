"""Add export_jobs for background data exports (F7.6, BRD N6)

One row per export a user asks for: what it holds, the filters it was taken
with, and where the finished file is. Kinds, formats and statuses are stored as
short text rather than PostgreSQL enum types, so adding one needs no migration.

Revision ID: 1e0496d719c2
Revises: e5b7c3d9a1f2
Create Date: 2026-09-27 17:29:03.274044

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "1e0496d719c2"
down_revision: str | Sequence[str] | None = "e5b7c3d9a1f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the export jobs table, indexed by owner."""
    op.create_table(
        "export_jobs",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum("receipts", "statistics", name="export_kind", native_enum=False, length=16),
            nullable=False,
        ),
        sa.Column(
            "format",
            sa.Enum("csv", "json", name="export_format", native_enum=False, length=16),
            nullable=False,
        ),
        sa.Column("params", sa.JSON(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "running",
                "ready",
                "failed",
                name="export_status",
                native_enum=False,
                length=16,
            ),
            nullable=False,
        ),
        sa.Column("object_name", sa.String(length=255), nullable=True),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("error", sa.String(length=500), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_export_jobs_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_export_jobs")),
    )
    op.create_index(op.f("ix_export_jobs_user_id"), "export_jobs", ["user_id"], unique=False)


def downgrade() -> None:
    """Drop it again."""
    op.drop_index(op.f("ix_export_jobs_user_id"), table_name="export_jobs")
    op.drop_table("export_jobs")
