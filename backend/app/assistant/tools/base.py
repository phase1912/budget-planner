"""What every assistant tool is, and how a new one joins (F21.7, ADR-0028).

A tool is a class in a module of this package: a `Reader` answers at once, a `Writer`
proposes a card the user approves and saves it through the service its screen uses, so
ownership (N2), quotas and every rule hold as they do on the screens. Defining the class
registers it — the graph, the prompt and the card's form follow without other changes.
"""

import abc
import difflib
import re
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Annotated, Any, ClassVar, Literal

from pydantic import BaseModel, BeforeValidator, Field

from app.assistant.core.ports import ToolSpec
from app.models.category import Category
from app.models.user import User
from app.ports.exchange_rates import ExchangeRatePort
from app.ports.goal_mapping import GoalMapperPort
from app.repository.category import CategoryRepository


def _plain_number(value: Any) -> Any:
    """An amount as people write it — "2 500", "2500 zł", "12,50" — as a plain number.

    A small model copies the user's own spelling into the arguments; refusing it dropped
    the whole request.
    """
    if not isinstance(value, str):
        return value
    digits = re.sub(r"[^\d.,-]", "", value)
    if "," in digits and "." in digits:
        digits = (
            digits.replace(",", "")
            if digits.rfind(".") > digits.rfind(",")
            else (digits.replace(".", "").replace(",", "."))
        )
    return digits.replace(",", ".")


Amount = Annotated[
    Decimal, BeforeValidator(_plain_number), Field(gt=0, max_digits=12, decimal_places=2)
]
"""A sum of money above zero, however the user wrote it."""

Balance = Annotated[Decimal, BeforeValidator(_plain_number), Field(max_digits=12, decimal_places=2)]
"""What is on an account: may be zero or below."""


@dataclass
class ToolContext:
    """What a tool runs with for one request: the signed-in user and their session."""

    session: Any
    user: User
    today: date
    rates: ExchangeRatePort | None = None
    goal_mapper: GoalMapperPort | None = None

    async def categories(self) -> list[Category]:
        """The categories the user's spending may go to: the shared ones and their own."""
        return list(await CategoryRepository(self.session).list_available(self.user.id))


@dataclass(frozen=True)
class Card:
    """A proposed write: what kind of thing, and its fields as the user may change them."""

    kind: str
    fields: dict[str, Any]


@dataclass(frozen=True)
class Answer:
    """What a read tool found: the figures for the model, the card for the user (F21.4)."""

    figures: str
    card: dict[str, Any] | None = None


FieldKind = Literal[
    "target", "text", "amount", "balance", "date", "day", "repeat", "category", "account",
    "choice", "switch", "percent", "items",
]  # fmt: skip


@dataclass(frozen=True)
class FormField:
    """One field of a card's form, as the screen draws it (F21.7.1).

    `target` names what the card changes or removes and cannot be edited; `day` is a day of
    the month; `repeat` is the pair `day`/`weekday`; `choice` offers `options`, each worded
    by the app; `category` and `account` pick one of the user's own; `items` lists names the
    user may take out one by one, with the ids beside them (`products` and `product_ids`).
    """

    name: str
    kind: FieldKind
    options: tuple[str, ...] = ()
    required: bool = True

    def to_json(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "kind": self.kind,
            "options": list(self.options),
            "required": self.required,
        }


REGISTRY: dict[str, "Tool"] = {}
"""Every tool, by name — filled as each tool class is defined."""
CARDS: dict[str, "Writer"] = {}
"""Every writer, by the kind of card it proposes."""


class Tool(abc.ABC):
    """One thing the assistant may do; a concrete subclass registers itself."""

    name: ClassVar[str]
    description: ClassVar[str]
    args: ClassVar[type[BaseModel]]
    writes: ClassVar[bool] = False

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if "name" not in cls.__dict__:
            return
        tool = cls()
        REGISTRY[cls.name] = tool
        if isinstance(tool, Writer):
            CARDS[tool.card_kind] = tool

    def spec(self) -> ToolSpec:
        """The tool as the model is offered it."""
        return ToolSpec(self.name, self.description, self.args.model_json_schema(), self.writes)


class Reader(Tool):
    """A tool that answers at once, from the user's own data."""

    @abc.abstractmethod
    async def read(self, ctx: ToolContext, args: Any) -> Answer:
        """The figures for the model and, where a screen shows them better, a card."""


class Writer(Tool):
    """A tool that proposes a card and, once the user approves it, saves it.

    `card` is what the user approves — the arguments resolved: names found, days filled
    in. `form` draws the card for a kind the app has no card of its own for.
    """

    writes = True
    card_kind: ClassVar[str]
    card: ClassVar[type[BaseModel]]
    form: ClassVar[tuple[FormField, ...]] = ()

    async def check(self, ctx: ToolContext, args: Any) -> str | None:
        """Why the arguments cannot become a card — a name the user has none of — or None."""
        return None

    @abc.abstractmethod
    async def propose(self, ctx: ToolContext, args: Any) -> dict[str, Any]:
        """The card's fields: the arguments resolved, ready to approve."""

    @abc.abstractmethod
    async def save(self, ctx: ToolContext, fields: Any) -> str:
        """Write the approved card through its service; what it created or changed.

        Raises whatever the service raises — the same refusals the screen shows.
        """


@dataclass(frozen=True)
class Found[T]:
    """What a name the user said points at: the one thing, or why there is none."""

    item: T | None = None
    error: str | None = None
    names: list[str] = field(default_factory=list)


def find_by_name[T](items: Sequence[T], said: str, name_of: Callable[[T], str]) -> Found[T]:
    """The item the user meant by `said`: the same name, else one containing it, else the
    closest by spelling. Two equally good, or none, is an error naming what there is, for
    the model to ask the user or try again."""
    names = [name_of(i) for i in items]
    wanted = said.strip().lower()
    if not items:
        return Found(error="the user has none", names=names)
    exact = [i for i in items if name_of(i).lower() == wanted]
    if len(exact) == 1:
        return Found(exact[0], names=names)
    within = [i for i in items if wanted and (wanted in name_of(i).lower())]
    if len(within) == 1:
        return Found(within[0], names=names)
    close = difflib.get_close_matches(wanted, [n.lower() for n in names], n=2, cutoff=0.6)
    if len(close) == 1:
        return Found(next(i for i in items if name_of(i).lower() == close[0]), names=names)
    return Found(
        error=f"no single one named {said!r}; there are: {', '.join(names) or 'none'}",
        names=names,
    )


def as_id(value: Any) -> uuid.UUID:
    """An id kept on a card as text."""
    return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))
