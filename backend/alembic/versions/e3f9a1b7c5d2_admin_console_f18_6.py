"""Plans granted by admins, the admin log and two-factor sign-in (F18.4, F18.6)

Revision ID: e3f9a1b7c5d2
Revises: d8e2f6a0c4b1
Create Date: 2026-10-17 18:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e3f9a1b7c5d2"
down_revision: str | Sequence[str] | None = "d8e2f6a0c4b1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _base_columns() -> list[sa.Column]:  # type: ignore[type-arg]
    return [
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    ]


def upgrade() -> None:
    """Add-only (ADR-0014): new tables and nullable or defaulted columns."""
    op.create_table(
        "plan_grants",
        *_base_columns(),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("plan", sa.String(16), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reason", sa.String(200), nullable=False),
        sa.Column("granted_by_id", sa.Uuid(), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_plan_grants_user_id_users"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["granted_by_id"],
            ["users.id"],
            name=op.f("fk_plan_grants_granted_by_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_plan_grants")),
    )
    op.create_index(op.f("ix_plan_grants_user_id"), "plan_grants", ["user_id"])
    op.create_table(
        "admin_actions",
        *_base_columns(),
        sa.Column("admin_id", sa.Uuid(), nullable=True),
        sa.Column("target_user_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.String(40), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["admin_id"],
            ["users.id"],
            name=op.f("fk_admin_actions_admin_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["target_user_id"],
            ["users.id"],
            name=op.f("fk_admin_actions_target_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_admin_actions")),
    )
    op.create_index(op.f("ix_admin_actions_admin_id"), "admin_actions", ["admin_id"])
    op.create_index(op.f("ix_admin_actions_target_user_id"), "admin_actions", ["target_user_id"])
    op.add_column("users", sa.Column("two_factor_secret", sa.String(255), nullable=True))
    op.add_column(
        "users", sa.Column("two_factor_enabled_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column("users", sa.Column("recovery_code_hashes", sa.JSON(), nullable=True))
    op.add_column(
        "refresh_tokens",
        sa.Column("second_factor", sa.Boolean(), server_default="false", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("refresh_tokens", "second_factor")
    op.drop_column("users", "recovery_code_hashes")
    op.drop_column("users", "two_factor_enabled_at")
    op.drop_column("users", "two_factor_secret")
    op.drop_table("admin_actions")
    op.drop_table("plan_grants")
