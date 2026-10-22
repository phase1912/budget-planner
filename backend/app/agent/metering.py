"""What every model call cost, and whose it was (F21.9.1, ADR-0030).

The agent measures each call itself — so no caller can forget to — and hands it to a
recorder as a `Spend`. Who pays is the signed-in user, or the one a background job names
with `charge_to`; work nobody asked for runs under `unasked` and is recorded but charged to
no one. One credit is 0.001 USD of the model's own price.
"""

import uuid
from collections.abc import Awaitable, Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from decimal import Decimal

from app.core.context import current_user_id

CREDIT_USD = Decimal("0.001")
"""What one credit stands for: a tenth of a cent of what the call cost us."""


class Purpose:
    """What a call was for, as the records and the wallet name it."""

    RECEIPT = "receipt"
    CATEGORIES = "categories"
    ASSISTANT = "assistant"
    SPEECH = "speech"
    GOAL_MAPPING = "goal_mapping"
    ADVICE = "advice"
    INCOME_DOCUMENT = "income_document"
    PRODUCTS = "products"


UNASKED = frozenset({Purpose.PRODUCTS})
"""Work that follows from what the user does without their asking for a model — matching
products when the list opens — and so is the service's cost, never the user's."""


@dataclass(frozen=True)
class Spend:
    """One call: what for, on which model, how much it took, and what it cost in credits."""

    purpose: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    audio_seconds: Decimal = Decimal(0)
    credits: Decimal = Decimal(0)
    user_id: uuid.UUID | None = None
    charged: bool = True


Recorder = Callable[[Spend], Awaitable[None]]
"""Keeps a spend; never raises — a call that cost money is never undone for its record."""

_payer: ContextVar[uuid.UUID | None] = ContextVar("ai_payer", default=None)
_unasked: ContextVar[bool] = ContextVar("ai_unasked", default=False)


@contextmanager
def charge_to(user_id: uuid.UUID) -> Iterator[None]:
    """Charge the calls made inside to `user_id`: for a job that runs after its request."""
    token = _payer.set(user_id)
    try:
        yield
    finally:
        _payer.reset(token)


@contextmanager
def unasked() -> Iterator[None]:
    """Record the calls made inside as nobody's: a scheduled pass, not a user's request."""
    token = _unasked.set(True)
    try:
        yield
    finally:
        _unasked.reset(token)


def credits_of(cost_usd: float | Decimal) -> Decimal:
    """A cost in USD as credits, to a thousandth of one."""
    return (Decimal(str(cost_usd)) / CREDIT_USD).quantize(Decimal("0.001"))


def spend(
    purpose: str,
    model: str,
    cost_usd: float | Decimal,
    *,
    input_tokens: int = 0,
    output_tokens: int = 0,
    audio_seconds: Decimal = Decimal(0),
) -> Spend:
    """A call's spend, paid by whoever is paying here, unless it is unasked work."""
    payer = _payer.get() or current_user_id.get()
    return Spend(
        purpose=purpose,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        audio_seconds=audio_seconds,
        credits=credits_of(cost_usd),
        user_id=payer,
        charged=payer is not None and not _unasked.get() and purpose not in UNASKED,
    )
