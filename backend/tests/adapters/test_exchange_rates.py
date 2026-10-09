"""Exchange-rate sources, against canned answers shaped like the real ones (F11.7.2)."""

from collections.abc import Callable
from datetime import date
from decimal import Decimal

import httpx
import pytest

from app.adapters.exchange_rates import (
    FallbackExchangeRates,
    FrankfurterExchangeRates,
    NbpExchangeRates,
)
from app.domain.currency import ExchangeRate
from app.ports.exchange_rates import ExchangeRateUnavailable

SATURDAY = date(2026, 10, 3)


def _nbp_rates(code: str, *rates: tuple[str, float]) -> dict[str, object]:
    return {
        "table": "A",
        "code": code,
        "rates": [{"no": "x", "effectiveDate": day, "mid": mid} for day, mid in rates],
    }


def _transport(answer: Callable[[httpx.Request], httpx.Response]) -> httpx.MockTransport:
    return httpx.MockTransport(answer)


def _nbp(tables: dict[tuple[str, str], dict[str, object]]) -> NbpExchangeRates:
    """An NBP whose tables hold `tables[(table, code)]`; everything else is a 404."""
    asked: list[str] = []

    def answer(request: httpx.Request) -> httpx.Response:
        parts = request.url.path.split("/")
        table, code = parts[4], parts[5].upper()
        asked.append(request.url.path)
        found = tables.get((table, code))
        return httpx.Response(200, json=found) if found else httpx.Response(404, text="Brak danych")

    return NbpExchangeRates(transport=_transport(answer))


@pytest.mark.asyncio
async def test_a_weekend_purchase_takes_the_last_rate_published_before_it() -> None:
    nbp = _nbp({("a", "UAH"): _nbp_rates("UAH", ("2026-10-01", 0.0864), ("2026-10-02", 0.0865))})

    rate = await nbp.rate("UAH", "PLN", SATURDAY)

    assert rate == ExchangeRate("UAH", "PLN", Decimal("0.0865"), date(2026, 10, 2), "NBP")


@pytest.mark.asyncio
async def test_a_dollar_account_converts_hryvnias_through_the_zloty() -> None:
    nbp = _nbp(
        {
            ("a", "UAH"): _nbp_rates("UAH", ("2026-10-02", 0.0864)),
            ("a", "USD"): _nbp_rates("USD", ("2026-10-02", 3.84)),
        }
    )

    rate = await nbp.rate("UAH", "USD", SATURDAY)

    assert rate.rate == Decimal("0.0225")
    assert rate.effective_date == date(2026, 10, 2)


@pytest.mark.asyncio
async def test_a_rarer_currency_is_found_in_the_weekly_table_b() -> None:
    nbp = _nbp({("b", "VND"): _nbp_rates("VND", ("2026-09-30", 0.00014822))})

    rate = await nbp.rate("VND", "PLN", SATURDAY)

    assert (rate.rate, rate.effective_date) == (Decimal("0.00014822"), date(2026, 9, 30))


@pytest.mark.asyncio
async def test_a_currency_in_neither_table_is_unavailable() -> None:
    with pytest.raises(ExchangeRateUnavailable):
        await _nbp({}).rate("XYZ", "PLN", SATURDAY)


@pytest.mark.asyncio
async def test_an_unreachable_nbp_is_unavailable_not_a_crash() -> None:
    def down(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down")

    with pytest.raises(ExchangeRateUnavailable):
        await NbpExchangeRates(transport=_transport(down)).rate("UAH", "PLN", SATURDAY)


@pytest.mark.asyncio
async def test_frankfurter_answers_with_the_date_it_published_for() -> None:
    def answer(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/2026-10-03"
        assert request.url.params["from"] == "USD"
        return httpx.Response(
            200, json={"amount": 1.0, "base": "USD", "date": "2026-10-02", "rates": {"PLN": 3.8998}}
        )

    rate = await FrankfurterExchangeRates(transport=_transport(answer)).rate("USD", "PLN", SATURDAY)

    assert rate == ExchangeRate("USD", "PLN", Decimal("3.8998"), date(2026, 10, 2), "ECB")


@pytest.mark.asyncio
async def test_frankfurter_without_the_currency_is_unavailable() -> None:
    def answer(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"message": "not found"})

    with pytest.raises(ExchangeRateUnavailable):
        await FrankfurterExchangeRates(transport=_transport(answer)).rate("UAH", "PLN", SATURDAY)


class _Fixed:
    def __init__(self, answer: ExchangeRate | None) -> None:
        self.answer = answer
        self.asked = 0

    async def rate(self, base: str, quote: str, on: date) -> ExchangeRate:
        self.asked += 1
        if self.answer is None:
            raise ExchangeRateUnavailable("none")
        return self.answer


@pytest.mark.asyncio
async def test_the_fallback_is_asked_only_when_the_first_source_has_no_rate() -> None:
    ecb_rate = ExchangeRate("USD", "PLN", Decimal("3.9"), SATURDAY, "ECB")
    nbp, ecb = _Fixed(None), _Fixed(ecb_rate)

    assert await FallbackExchangeRates(nbp, ecb).rate("USD", "PLN", SATURDAY) == ecb_rate
    assert (nbp.asked, ecb.asked) == (1, 1)


@pytest.mark.asyncio
async def test_with_no_source_answering_the_rate_is_unavailable() -> None:
    with pytest.raises(ExchangeRateUnavailable):
        await FallbackExchangeRates(_Fixed(None), _Fixed(None)).rate("UAH", "PLN", SATURDAY)


@pytest.mark.asyncio
async def test_the_same_currency_needs_no_source() -> None:
    source = _Fixed(None)

    rate = await FallbackExchangeRates(source).rate("PLN", "PLN", SATURDAY)

    assert (rate.rate, source.asked) == (Decimal(1), 0)
