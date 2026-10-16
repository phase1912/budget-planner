"""User entity (F1.1.1)."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.email_intake import new_forwarding_token
from app.models.base import Model


class User(Model):
    """An account in the system (BRD section 9).

    Holds identity, credentials, account-level preferences (currency, budget),
    and authorization role.
    """

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    first_name: Mapped[str] = mapped_column(String(50), nullable=False)
    last_name: Mapped[str] = mapped_column(String(50), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    # When the owner proved the address is theirs (F17.8.2); None until then.
    email_confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    currency: Mapped[str] = mapped_column(
        String(3), default="USD", server_default="USD", nullable=False
    )
    budget_limit: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    # The language the user chose to read the product in (F9.9); None until they choose,
    # when the client goes by the browser's language instead.
    language: Mapped[str | None] = mapped_column(String(2), nullable=True)

    role: Mapped[str] = mapped_column(String, default="user", server_default="user", nullable=False)
    # The secret part of the user's receipt forwarding address (F11.2); the domain
    # is configuration, so moving where mail lands needs no migration.
    forwarding_token: Mapped[str] = mapped_column(
        String(32), unique=True, default=new_forwarding_token, nullable=False
    )

    @property
    def email_confirmed(self) -> bool:
        """Whether the owner has proved the address is theirs (F17.8.2)."""
        return self.email_confirmed_at is not None
