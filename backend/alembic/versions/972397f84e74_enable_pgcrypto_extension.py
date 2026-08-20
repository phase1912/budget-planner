"""enable pgcrypto extension

Baseline migration for F0.3.4. Enables `pgcrypto`, needed for the pgp_sym_encrypt/
pgp_sym_decrypt functions that will back encryption at rest for receipt images and
extracted financial fields (BRD N1) once those tables exist.

Does not create `uuid-ossp` or any other UUID-generation extension: model primary
keys use `gen_random_uuid()` (see app.models.base.Model), which has been built into
PostgreSQL core since version 13 and needs no extension enabled.

Revision ID: 972397f84e74
Revises:
Create Date: 2026-08-20 13:10:59.867517

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "972397f84e74"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP EXTENSION IF EXISTS pgcrypto")
