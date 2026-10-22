"""The tools bound to one request, as the conversation service calls them (F21.1, F21.7).

A read tool answers at once. A write tool only turns its arguments into a card; the card
is written when the user approves it, through the same service the screen calls, so
ownership (N2), quotas and every rule hold as they do on the screens. Settings and the
account have no tool.
"""

import json
from datetime import date
from typing import Any

from pydantic import ValidationError

from app.api.errors import DomainError, ProblemCode
from app.assistant.core.ports import ToolCall, ToolSpec
from app.assistant.tools import all_tools, card_writers
from app.assistant.tools.base import Card, FormField, Reader, ToolContext, Writer
from app.assistant.tools.overview import known
from app.models.category import Category
from app.models.user import User
from app.ports.exchange_rates import ExchangeRatePort
from app.ports.goal_mapping import GoalMapperPort


def tool_specs() -> list[ToolSpec]:
    """Every tool the assistant is offered, with its arguments' schema."""
    return [tool.spec() for tool in all_tools().values()]


def card_form(kind: str) -> list[dict[str, Any]] | None:
    """How a card of `kind` is drawn when the app has no card of its own for it."""
    writer = card_writers().get(kind)
    if writer is None or not writer.form:
        return None
    return [f.to_json() for f in writer.form]


def _errors(exc: ValidationError) -> str:
    return "; ".join(f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in exc.errors())


class Toolbox:
    """The tools, bound to the signed-in user and their session for one request."""

    def __init__(
        self,
        session: Any,
        user: User,
        today: date,
        rates: ExchangeRatePort | None = None,
        goal_mapper: GoalMapperPort | None = None,
    ) -> None:
        self.ctx = ToolContext(session, user, today, rates, goal_mapper)
        self.answers: dict[str, Card] = {}
        """The answer card of each read tool used this turn, the latest kept (F21.4)."""

    async def categories(self) -> list[Category]:
        """The categories the user's spending may go to."""
        return await self.ctx.categories()

    async def known(self) -> str:
        """What the user has, for the model to resolve what they mean (F21.13.2)."""
        return await known(self.ctx)

    async def read(self, call: ToolCall) -> str:
        """Run a read tool; a call the model got wrong is answered as such, not raised.

        A tool that has a card to show (F21.4) leaves it in `answers`.
        """
        tool = all_tools().get(call.name)
        if not isinstance(tool, Reader):
            return json.dumps({"error": f"no read tool {call.name}"})
        try:
            answer = await tool.read(self.ctx, tool.args.model_validate(call.args))
        except (ValidationError, ValueError) as exc:
            return json.dumps({"error": str(exc)})
        if answer.card is not None:
            self.answers[call.name] = Card("answer", answer.card)
        return answer.figures

    async def check(self, call: ToolCall) -> str | None:
        """Why a write call cannot become a card, for the model to fix; None when it can."""
        tool = all_tools().get(call.name)
        if not isinstance(tool, Writer):
            return f"no write tool {call.name}"
        try:
            args = tool.args.model_validate(call.args)
        except ValidationError as exc:
            return _errors(exc)
        return await tool.check(self.ctx, args)

    async def propose(self, call: ToolCall) -> Card | None:
        """The card a write tool proposes, or None for a call that cannot become one."""
        tool = all_tools().get(call.name)
        if not isinstance(tool, Writer):
            return None
        try:
            args = tool.args.model_validate(call.args)
        except ValidationError:
            return None
        if await tool.check(self.ctx, args):
            return None
        return Card(tool.card_kind, await tool.propose(self.ctx, args))

    async def save(self, card: Card) -> str:
        """Write an approved card through its service; returns what it created.

        Raises DomainError (invalid_card) for fields that do not hold, and whatever the
        service raises — the same refusals the screen would show.
        """
        writer = card_writers().get(card.kind)
        if writer is None:
            raise DomainError("This card cannot be saved.", code=ProblemCode.INVALID_CARD)
        try:
            fields = writer.card.model_validate(card.fields)
        except ValidationError as exc:
            raise DomainError("Check the card's fields.", code=ProblemCode.INVALID_CARD) from exc
        return await writer.save(self.ctx, fields)


__all__ = ["Card", "FormField", "Toolbox", "card_form", "tool_specs"]
