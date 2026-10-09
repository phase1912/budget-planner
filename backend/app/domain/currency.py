"""Converting a foreign receipt into the account's currency (F11.7, ADR-0016)."""

import copy
import re
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

CENT = Decimal("0.01")
RATE_PLACES = Decimal("0.00000001")
_ISO_CODE = re.compile(r"^[A-Z]{3}$")


@dataclass(frozen=True)
class ExchangeRate:
    """How many units of `quote` one unit of `base` bought, as published for a day.

    `effective_date` is the day of the table the rate comes from, which is the purchase
    date or the last working day before it (ADR-0016); `source` names the publisher.
    """

    base: str
    quote: str
    rate: Decimal
    effective_date: date
    source: str


def receipt_currency(extraction: dict[str, Any], account_currency: str) -> str:
    """The currency a receipt was paid in: the one read off it, else the account's.

    A code that is not three capital letters is a misreading, not a currency, so it is
    treated as unread rather than sent to a rate source.
    """
    code = str(extraction.get("currency") or "").strip().upper()
    return code if _ISO_CODE.match(code) else account_currency


def convert(amount: Decimal, rate: Decimal) -> Decimal:
    """`amount` at `rate`, to the cent, half up (ADR-0016)."""
    return (amount * rate).quantize(CENT, rounding=ROUND_HALF_UP)


def convert_receipt(
    total: Decimal | None, lines: list[Decimal], rate: Decimal
) -> tuple[Decimal | None, list[Decimal]]:
    """A receipt's total and line totals at `rate`, still adding up if they did before.

    Rounding each line on its own can leave the lines a cent or two off the converted
    total; that remainder goes on the largest line, so a receipt that balanced in its own
    currency balances in the account's and is not sent to review over rounding (A9).
    """
    converted_lines = [convert(line, rate) for line in lines]
    if total is None:
        return None, converted_lines
    converted_total = convert(total, rate)
    if lines and sum(lines, Decimal(0)) == total:
        remainder = converted_total - sum(converted_lines, Decimal(0))
        largest = max(range(len(lines)), key=lambda i: abs(lines[i]))
        converted_lines[largest] += remainder
    return converted_total, converted_lines


def _amount(value: Any) -> Decimal | None:
    if value is None or str(value).strip() == "":
        return None
    try:
        return Decimal(str(value).replace(",", "."))
    except InvalidOperation:
        return None


def _money(value: Decimal | None) -> str | None:
    return None if value is None else str(value)


def _counted_lines(extraction: dict[str, Any]) -> set[int]:
    """Indices of the lines stored: a line matched as the same as another is not (B2)."""
    repeated = {
        match.get("item_b_index")
        for match in extraction.get("position_matches") or []
        if isinstance(match, dict) and match.get("result") == "same"
    }
    items = extraction.get("line_items") or []
    return {i for i in range(len(items)) if i not in repeated}


def conversion_preview(extraction: dict[str, Any], rate: ExchangeRate) -> dict[str, Any]:
    """What the wizard shows before storing: the rate and the total it gives (F11.7.4).

    The amounts stay in the receipt's currency until it is stored, so a total the user
    corrects in the wizard is converted as corrected.
    """
    total = _amount(extraction.get("receipt_total"))
    return {
        "currency": rate.base,
        "account_currency": rate.quote,
        "rate": str(rate.rate),
        "rate_date": rate.effective_date.isoformat(),
        "source": rate.source,
        "converted_total": _money(convert(total, rate.rate) if total is not None else None),
    }


def convert_extraction(extraction: dict[str, Any], rate: ExchangeRate) -> dict[str, Any]:
    """A copy of `extraction` in the account's currency, keeping what was printed (D1).

    The total and every line are converted; the original currency, total, rate, its date
    and source are recorded beside them so the figure can be traced back (ADR-0016).
    """
    converted = copy.deepcopy(extraction)
    items: list[dict[str, Any]] = [
        i for i in converted.get("line_items") or [] if isinstance(i, dict)
    ]
    counted = sorted(_counted_lines(converted) & set(range(len(items))))
    printed = {i: _amount(items[i].get("total_price")) for i in range(len(items))}
    lines = [printed[i] or Decimal(0) for i in counted]
    total = _amount(converted.get("receipt_total"))
    new_total, new_lines = convert_receipt(total, lines, rate.rate)
    new_prices = dict(zip(counted, new_lines, strict=True))
    for i, item in enumerate(items):
        price = printed[i]
        unit = _amount(item.get("unit_price"))
        if i in new_prices:
            item["total_price"] = str(new_prices[i])
        elif price is not None:
            item["total_price"] = str(convert(price, rate.rate))
        if unit is not None:
            item["unit_price"] = str(
                new_prices[i] if unit == price and i in new_prices else convert(unit, rate.rate)
            )
    computed = _amount(converted.get("computed_total"))
    if computed is not None:
        converted["computed_total"] = str(convert(computed, rate.rate))
    converted.update(
        receipt_total=_money(new_total),
        currency=rate.quote,
        original_currency=rate.base,
        original_total=_money(total),
        exchange_rate=str(rate.rate),
        exchange_rate_date=rate.effective_date.isoformat(),
        exchange_rate_source=rate.source,
    )
    converted.pop("conversion", None)
    return converted


def unconverted(extraction: dict[str, Any], currency: str) -> dict[str, Any]:
    """A foreign receipt no rate was found for: held in review in its printed amounts.

    It is never counted as if it were in the account's currency (A11, D3); the missing
    rate is recorded as its original currency with no rate, which is what the review shows.
    """
    held = dict(extraction)
    held.update(
        original_currency=currency,
        original_total=extraction.get("receipt_total"),
        exchange_rate=None,
        requires_manual_review=True,
    )
    held.pop("conversion", None)
    return held
