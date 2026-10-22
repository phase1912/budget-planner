import asyncio
import json
import logging

from pydantic import BaseModel, Field

from app.agent.core import Agent
from app.agent.metering import Purpose
from app.agent.types import Message
from app.ports.product_matching import MatchQuestion, ProductMatcherPort

logger = logging.getLogger(__name__)

PROMPT = """\
Shop receipts print one product in many ways: abbreviated ("Nat." for "Naturalny"),
in capitals, with words glued together ("JajkoNiespodzian"), with a tax letter or a
code at the end. For each printed name below, decide whether it is the same product as
one of its candidates. A candidate lists every way it has been printed, separated by
" / ". All candidates are already the same package size.

Answer the candidate's reference when the names differ only in spelling like that —
same brand, same kind of product, same variety. Answer null when the variety, flavour,
fat content or brand differs, or when nothing points to the same product.

Examples:
- "Jogurt Nat. Pilos 330g" vs "JOGURT NATURALNY PILOS 330G" -> same
- "Jajko Kinder Niespodz 20g" vs "JAJKO Kinder 20g A / JajkoNiespodzian20g" -> same
- "Chipsy Lays Papryka 140g" vs "Chipsy Lays Solone 140g" -> null (another flavour)
- "MlekoSw3,2 1l" vs "Mleko Spoz 2 1l" -> null (another fat content)
"""


class _Answer(BaseModel):
    name: str = Field(description="The printed name, exactly as given.")
    candidate: str | None = Field(
        description="The reference of the candidate it is the same product as, or null."
    )


class _Answers(BaseModel):
    answers: list[_Answer]


class ProductMatchingAdapter(ProductMatcherPort):
    """Asks an LLM which product an ambiguous printed name is, behind `ProductMatcherPort`.

    One call for every question, bounded by `timeout_seconds`. Only references that
    were offered for that name are kept; anything else counts as none (F16.1).
    """

    def __init__(self, agent: Agent, timeout_seconds: float = 30.0) -> None:
        self._agent = agent
        self._timeout_seconds = timeout_seconds

    async def match(self, questions: list[MatchQuestion]) -> dict[str, str | None]:
        """See ProductMatcherPort.match. Never raises."""
        unanswered: dict[str, str | None] = {q.name: None for q in questions}
        if not questions:
            return unanswered
        payload = [{"name": q.name, "candidates": q.candidates} for q in questions]
        text = f"{PROMPT}\nNames:\n{json.dumps(payload, ensure_ascii=False, indent=2)}"
        try:
            async with asyncio.timeout(self._timeout_seconds):
                parsed = await self._agent.run_structured(
                    [Message(role="user", content=[{"type": "text", "text": text}])],
                    schema=_Answers,
                    temperature=0.0,
                    purpose=Purpose.PRODUCTS,
                )
        except Exception:
            logger.exception("Product matching failed; every name stays its own product")
            return unanswered
        offered = {q.name: q.candidates for q in questions}
        for answer in parsed.answers:
            if answer.name in offered and answer.candidate in offered[answer.name]:
                unanswered[answer.name] = answer.candidate
        return unanswered
