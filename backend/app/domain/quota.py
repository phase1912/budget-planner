"""An account's AI credits this month (F21.9, ADR-0030; was the receipt quota of F10.6).

Every model call costs money, so what is spent, not what is stored, is counted and capped:
one monthly wallet of credits for reading receipts, talking and speaking to the assistant
and asking about goals. Months are calendar months in UTC, like every other month in the
product (ADR-0009).
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from decimal import Decimal


def month_start(day: date) -> date:
    """The first day of `day`'s month."""
    return day.replace(day=1)


def next_month_start(day: date) -> date:
    """The first day of the month after `day`'s: when a monthly quota starts afresh."""
    return date(day.year + day.month // 12, day.month % 12 + 1, 1)


def start_of(day: date) -> datetime:
    """Midnight UTC at the start of `day`."""
    return datetime.combine(day, time(), tzinfo=UTC)


@dataclass(frozen=True)
class CreditWallet:
    """One account's AI credits this month against its plan (F21.9, ADR-0030).

    Credits are what the account's model calls cost, one to 0.001 USD; `used` counts the
    month's charged calls and the receipts being read now, at what a receipt costs, so a
    burst of uploads cannot overdraw it. `limit` is None for an account without one (an
    admin). The user never sees credits: `receipts_left` and `messages_left` say what is
    left as either, at what each has lately cost (`per_receipt`, `per_message`).
    """

    limit: int | None
    used: Decimal
    resets_on: date
    per_receipt: Decimal
    per_message: Decimal
    plan: str = "free"
    plan_ends_on: date | None = None
    ad_free: bool = False

    @property
    def unlimited(self) -> bool:
        """Whether the account may spend any number of credits."""
        return self.limit is None

    @property
    def remaining(self) -> Decimal | None:
        """Credits left this month, never below zero; None when unlimited."""
        return None if self.limit is None else max(Decimal(self.limit) - self.used, Decimal(0))

    @property
    def receipts_left(self) -> int | None:
        """About how many receipts the credits left would read."""
        return _how_many(self.remaining, self.per_receipt)

    @property
    def messages_left(self) -> int | None:
        """About how many messages to the assistant the credits left would answer."""
        return _how_many(self.remaining, self.per_message)

    def allows(self, credits: Decimal) -> bool:
        """Whether something costing `credits` may still start this month."""
        remaining = self.remaining
        return remaining is None or remaining >= credits


def _how_many(remaining: Decimal | None, each: Decimal) -> int | None:
    if remaining is None:
        return None
    return int(remaining // each) if each > 0 else 0


SPEECH_USD_PER_MINUTE = Decimal("0.016")
"""What Speech-to-Text charges a minute of sound (ADR-0031)."""


def speech_credits(seconds: Decimal) -> Decimal:
    """What `seconds` of recording cost to recognise, in credits."""
    return (seconds * SPEECH_USD_PER_MINUTE / 60 / Decimal("0.001")).quantize(Decimal("0.001"))
