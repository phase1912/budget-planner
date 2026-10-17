"""What admins may do to an account, and the limits on it (F18.6).

Admins support accounts — never read them: nothing here reaches a receipt (BRD N2).
"""

from datetime import datetime, timedelta
from enum import StrEnum
from typing import Final

MAX_GRANT_DAYS: Final = 366
"""The longest plan one grant gives: a year; a longer one is a second grant later."""


class AdminActionKind(StrEnum):
    """Every action written to the admin log (F18.6.3)."""

    EMAIL_CONFIRMED = "email_confirmed"
    CONFIRMATION_SENT = "confirmation_sent"
    PASSWORD_RESET_SENT = "password_reset_sent"
    PLAN_GRANTED = "plan_granted"
    PLAN_REVOKED = "plan_revoked"
    ADMIN_APPOINTED = "admin_appointed"
    ADMIN_REMOVED = "admin_removed"


def grant_period(
    days: int, running_until: datetime | None, now: datetime
) -> tuple[datetime, datetime]:
    """When a new grant of `days` runs: from now, or straight after the plan running now.

    Granting again while a plan runs therefore extends it rather than overlapping it, so
    "add 30 days" means 30 more days (F18.6.3).
    """
    starts = max(running_until or now, now)
    return starts, starts + timedelta(days=days)
