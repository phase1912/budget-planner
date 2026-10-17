"""User entity (F1.1.1)."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import JSON, Boolean, Date, DateTime, Numeric, SmallInteger, String
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
    # When, and to which version of, the terms and privacy policy the owner agreed at
    # sign-up (F17.9.4); None for accounts opened before acceptance was asked.
    terms_accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    terms_version: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # The authenticator secret, encrypted (F18.6.1); set while setting up, in force once
    # `two_factor_enabled_at` is set. Recovery codes are kept as hashes, used ones removed.
    two_factor_secret: Mapped[str | None] = mapped_column(String(255), nullable=True)
    two_factor_enabled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    recovery_code_hashes: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
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

    # How the product looks and opens for the owner, on every device (F23.1, F23.9): the
    # palette (None: the default), whether it turns dark when the device does, and when
    # the first-sign-in setup was finished or skipped (None: show it).
    palette: Mapped[str | None] = mapped_column(String(16), nullable=True)
    dark_at_night: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )
    onboarded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Shows business trips — per diem and the settlement (F23.12); off for most people.
    travels_for_work: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )
    # What usually comes in a month, standing in until the month's income is entered,
    # and the day it comes (F23.10); months stay calendar months whatever the payday.
    usual_income: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    payday: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    # Money on the user's accounts on `balance_since` (F23.14); the balance then moves by
    # itself with income and counted purchases. None: no balance is shown.
    starting_balance: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    balance_since: Mapped[date | None] = mapped_column(Date, nullable=True)

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

    @property
    def two_factor_enabled(self) -> bool:
        """Whether signing in needs an authenticator code after the password (F18.6.1)."""
        return self.two_factor_enabled_at is not None
