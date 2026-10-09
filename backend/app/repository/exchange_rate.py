"""Fetched exchange rates, kept so each is asked for once (F11.7.2, ADR-0016)."""

from datetime import date

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.currency import ExchangeRate
from app.models.exchange_rate import CachedExchangeRate
from app.ports.exchange_rates import ExchangeRatePort


class CachedExchangeRates:
    """An ExchangeRatePort that answers from the database before asking `source`.

    Rates are public and fixed once published, so the cache is shared across users and
    never expires; a pair and date not cached is fetched once and kept. Raises what
    `source` raises, ExchangeRateUnavailable, when neither has the rate.
    """

    def __init__(self, source: ExchangeRatePort, session: AsyncSession) -> None:
        self.source = source
        self.session = session

    async def rate(self, base: str, quote: str, on: date) -> ExchangeRate:
        """The cached rate for the pair on `on`, else the source's, which is then cached."""
        stmt = select(CachedExchangeRate).where(
            CachedExchangeRate.base == base,
            CachedExchangeRate.quote == quote,
            CachedExchangeRate.requested_date == on,
        )
        cached = (await self.session.execute(stmt)).scalar_one_or_none()
        if cached is not None:
            return ExchangeRate(base, quote, cached.rate, cached.effective_date, cached.source)
        fetched = await self.source.rate(base, quote, on)
        await self.session.execute(
            insert(CachedExchangeRate)
            .values(
                base=base,
                quote=quote,
                requested_date=on,
                rate=fetched.rate,
                effective_date=fetched.effective_date,
                source=fetched.source,
            )
            .on_conflict_do_nothing()
        )
        return fetched
