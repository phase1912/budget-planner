"""Reads a payslip or transfer confirmation into an income entry, via the Agent (F23.11)."""

import re
from datetime import date
from decimal import Decimal, InvalidOperation

from pydantic import BaseModel, Field

from app.adapters.vision_agent import content_part, readable_input
from app.agent.core import Agent
from app.agent.types import Message
from app.domain.income import IncomeKind
from app.ports.income_reading import IncomeReaderPort, IncomeReading

PROMPT = """You are reading a document a user uploaded as money they received: a payslip,
a bank transfer confirmation, an invoice paid to them, a refund confirmation.

Return:
- is_income: true only if the document shows money coming IN to the user. A shop receipt,
  a bill, or a payment the user made is not income: return false and leave the rest empty.
- amount: the net amount actually received (on a payslip, the net pay "do wypłaty" /
  "netto" / "до виплати", never gross), digits with a dot for decimals, no currency.
- received_on: the date the money arrived or the pay date, as YYYY-MM-DD; empty if absent.
- source: who paid, short — an employer's or payer's name, at most 60 characters.
- kind: "salary" for pay from an employer, "side" for freelance or other earnings,
  "refund" for money given back, "other" otherwise.
Leave a field empty rather than guess."""


class IncomeDocumentResponse(BaseModel):
    """The model's reading of an income document."""

    is_income: bool
    amount: str | None = Field(default=None, description="Net amount received, e.g. 6800.00")
    received_on: str | None = Field(default=None, description="YYYY-MM-DD")
    source: str | None = None
    kind: IncomeKind = IncomeKind.OTHER


class IncomeDocumentAdapter(IncomeReaderPort):
    """Sends one document to the model and tidies its answer (F23.11).

    The document is only held for the call; nothing about it is stored here.
    """

    def __init__(self, agent: Agent) -> None:
        self._agent = agent

    async def read(self, data: bytes, mime_type: str) -> IncomeReading:
        """Read the money received; an amount or date the model garbled comes back None."""
        data, mime_type = readable_input(data, mime_type)
        messages = [
            Message(
                role="user",
                content=[{"type": "text", "text": PROMPT}, content_part(data, mime_type)],
            )
        ]
        answer = await self._agent.run_structured(
            messages, schema=IncomeDocumentResponse, max_tokens=2048, reasoning=False
        )
        if not answer.is_income:
            return IncomeReading(False, None, None, None, IncomeKind.OTHER)
        return IncomeReading(
            True,
            _amount(answer.amount),
            _day(answer.received_on),
            (answer.source or "").strip()[:60] or None,
            answer.kind,
        )


def _amount(text: str | None) -> Decimal | None:
    if not text:
        return None
    cleaned = re.sub(r"[^\d.,-]", "", text).replace(",", ".")
    try:
        value = Decimal(cleaned).quantize(Decimal("0.01"))
    except InvalidOperation:
        return None
    return value if value > 0 else None


def _day(text: str | None) -> date | None:
    try:
        return date.fromisoformat(text) if text else None
    except ValueError:
        return None
