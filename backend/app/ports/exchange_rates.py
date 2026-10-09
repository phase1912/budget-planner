from datetime import date
from typing import Protocol

from app.domain.currency import ExchangeRate


class ExchangeRateUnavailable(Exception):
    """No rate could be found for a pair on a date: the source is down or lacks a currency."""


class ExchangeRatePort(Protocol):
    """Exchange rates for converting foreign receipts (F11.7, ADR-0016)."""

    async def rate(self, base: str, quote: str, on: date) -> ExchangeRate:
        """The rate from `base` to `quote` published for `on`, else the last one before it.

        Raises ExchangeRateUnavailable — and nothing else — when there is none, so the
        caller can hold the receipt in review instead of failing the intake (A11).
        """
        ...
