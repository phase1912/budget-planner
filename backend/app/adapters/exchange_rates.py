"""Exchange rates from public, keyless sources (F11.7, ADR-0016)."""

import logging
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx

from app.domain.currency import RATE_PLACES, ExchangeRate
from app.ports.exchange_rates import ExchangeRatePort, ExchangeRateUnavailable

logger = logging.getLogger(__name__)

LOOKBACK = timedelta(days=14)
"""How far before the purchase date a rate may come from: a table B week and a holiday."""

_TIMEOUT = httpx.Timeout(10.0)


def _today() -> date:
    return datetime.now(UTC).date()


class NbpExchangeRates:
    """The National Bank of Poland's mid rates, tables A then B, crossed through the złoty.

    Every NBP rate is a price in złoty, so UAH → USD is the UAH mid over the USD mid.
    """

    source = "NBP"

    def __init__(
        self,
        base_url: str = "https://api.nbp.pl/api",
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.transport = transport

    async def rate(self, base: str, quote: str, on: date) -> ExchangeRate:
        """The cross rate from `base` to `quote` for `on`, from the latest tables up to it."""
        async with httpx.AsyncClient(transport=self.transport, timeout=_TIMEOUT) as client:
            base_mid, base_date = await self._mid(client, base, on)
            quote_mid, quote_date = await self._mid(client, quote, on)
        return ExchangeRate(
            base=base,
            quote=quote,
            rate=(base_mid / quote_mid).quantize(RATE_PLACES),
            effective_date=min(base_date, quote_date),
            source=self.source,
        )

    async def _mid(self, client: httpx.AsyncClient, code: str, on: date) -> tuple[Decimal, date]:
        """The price of one `code` in złoty on the last table published up to `on`."""
        end = min(on, _today())
        if code == "PLN":
            return Decimal(1), end
        start = end - LOOKBACK
        for table in ("a", "b"):
            url = f"{self.base_url}/exchangerates/rates/{table}/{code.lower()}/{start}/{end}/"
            try:
                response = await client.get(url, params={"format": "json"})
            except httpx.HTTPError as error:
                raise ExchangeRateUnavailable(f"NBP unreachable: {error}") from error
            if response.status_code == 404:
                continue
            if response.status_code != 200:
                raise ExchangeRateUnavailable(f"NBP answered {response.status_code}")
            return _last_mid(response.json())
        raise ExchangeRateUnavailable(f"NBP has no {code} rate up to {end}")


def _last_mid(payload: Any) -> tuple[Decimal, date]:
    try:
        last = payload["rates"][-1]
        return Decimal(str(last["mid"])), date.fromisoformat(last["effectiveDate"])
    except (KeyError, IndexError, TypeError, ValueError, InvalidOperation) as error:
        raise ExchangeRateUnavailable("NBP answered something unreadable") from error


class FrankfurterExchangeRates:
    """The ECB's reference rates through Frankfurter; about 30 currencies, no hryvnia."""

    source = "ECB"

    def __init__(
        self,
        base_url: str = "https://api.frankfurter.app",
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.transport = transport

    async def rate(self, base: str, quote: str, on: date) -> ExchangeRate:
        """The rate for `on`; Frankfurter itself answers the last one before a day off."""
        day = min(on, _today())
        try:
            async with httpx.AsyncClient(
                transport=self.transport, timeout=_TIMEOUT, follow_redirects=True
            ) as client:
                response = await client.get(
                    f"{self.base_url}/{day}", params={"from": base, "to": quote}
                )
        except httpx.HTTPError as error:
            raise ExchangeRateUnavailable(f"Frankfurter unreachable: {error}") from error
        if response.status_code != 200:
            raise ExchangeRateUnavailable(f"Frankfurter has no {base}/{quote} rate")
        try:
            payload = response.json()
            rate = Decimal(str(payload["rates"][quote]))
            published = date.fromisoformat(payload["date"])
        except (KeyError, TypeError, ValueError, InvalidOperation) as error:
            raise ExchangeRateUnavailable("Frankfurter answered something unreadable") from error
        return ExchangeRate(base, quote, rate.quantize(RATE_PLACES), published, self.source)


class FallbackExchangeRates:
    """Asks each source in turn and answers with the first that has the rate (ADR-0016)."""

    def __init__(self, *sources: ExchangeRatePort) -> None:
        self.sources = sources

    async def rate(self, base: str, quote: str, on: date) -> ExchangeRate:
        """The first source's answer; ExchangeRateUnavailable only when none has one."""
        if base == quote:
            return ExchangeRate(base, quote, Decimal(1), on, "same currency")
        for source in self.sources:
            try:
                return await source.rate(base, quote, on)
            except ExchangeRateUnavailable as error:
                logger.info("No %s/%s rate for %s: %s", base, quote, on, error)
        raise ExchangeRateUnavailable(f"No source has a {base}/{quote} rate for {on}")
