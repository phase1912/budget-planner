from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class MatchQuestion:
    """A printed line name the rules could not place, and the products it might be (F16.1).

    `candidates` maps a reference the answer uses to a product's names — every way it has
    been printed, joined by " / "; all are of the line's package size.
    """

    name: str
    candidates: dict[str, str]


class ProductMatcherPort(Protocol):
    """Judges which product, if any, an ambiguous printed name is (F16.1)."""

    async def match(self, questions: list[MatchQuestion]) -> dict[str, str | None]:
        """For each question's name, the candidate reference it is, or None for none of them.

        Never raises: when no answer can be had, every name maps to None and becomes a
        product of its own, which the user can merge by hand.
        """
        ...
