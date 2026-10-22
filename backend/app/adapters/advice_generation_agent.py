import asyncio
import logging

from pydantic import BaseModel, Field

from app.agent.core import Agent
from app.agent.metering import Purpose
from app.agent.types import Message
from app.domain.advice import Advice, AdviceTarget
from app.domain.goal_analysis import GoalAnalysis, evidence_refs, render_advice_context
from app.ports.advice_generation import AdviceGeneratorPort, AdviceUnavailable

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You advise one person on one goal, using only the evidence below, which comes from
their own receipts.

Rules:
- Every recommendation targets exactly one category, recurring purchase or product
  that the evidence names, by the reference in brackets before it, e.g. "c2" or
  "i1". Nothing else.
- Say what to do, concretely: stop, swap, halve, cap at an amount, buy less often.
- Justify it with figures from the evidence: how often, how much, where, the rise.
- Never give general financial tips ("track your spending", "reduce discretionary
  spending", "make a budget"). If the evidence supports nothing specific, return
  no recommendations at all.
- Write amounts in the currency the evidence uses. At most three recommendations,
  the most effective first.
- Say what share of the spending on the target the action removes: 100 to stop
  buying it, 50 to halve it. Never state what it saves; the app works that out
  from the receipts.
- A product in "Prices of what the user buys" may be the target. Where it costs less
  in another shop, the advice may be to buy it there, naming the shop; the share is
  then how many of its purchases to move there, 100 for all of them.
"""


LANGUAGE_NAMES = {"en": "English", "uk": "Ukrainian", "pl": "Polish"}


class _Recommendation(BaseModel):
    target_ref: str = Field(
        description="The reference in brackets before the target in the evidence, e.g. c2."
    )
    action: str = Field(
        description="What to do, in one short sentence, e.g. 'Stop buying Cola 0.5'."
    )
    rationale: str = Field(description="Why, citing figures from the evidence.")
    reduction_percent: int = Field(
        ge=1, le=100, description="Share of the spending on the target the action removes."
    )


class _AdviceResponse(BaseModel):
    recommendations: list[_Recommendation]


class AdviceGenerationAdapter(AdviceGeneratorPort):
    """Proposes recommendations with an LLM, behind `AdviceGeneratorPort` (BRD F3).

    `timeout_seconds` bounds the whole call, retries included: the user is
    waiting on the request that asked for advice.
    """

    def __init__(self, agent: Agent, timeout_seconds: float = 30.0) -> None:
        self._agent = agent
        self._timeout_seconds = timeout_seconds

    async def propose(
        self, analysis: GoalAnalysis, currency: str, *, language: str = "en"
    ) -> list[Advice]:
        """Ask the model; see AdviceGeneratorPort.propose. Raises AdviceUnavailable."""
        evidence = render_advice_context(analysis, currency)
        written_in = (
            f"- Write `action` and `rationale` in {LANGUAGE_NAMES.get(language, 'English')}.\n"
        )
        prompt = f"{SYSTEM_PROMPT}{written_in}\nEvidence:\n{evidence}"
        messages = [Message(role="user", content=[{"type": "text", "text": prompt}])]
        try:
            async with asyncio.timeout(self._timeout_seconds):
                answer = await self._agent.run_structured(
                    messages, schema=_AdviceResponse, temperature=0.0, purpose=Purpose.ADVICE
                )
        except Exception as error:
            logger.exception("Advice generation failed")
            raise AdviceUnavailable from error
        return targeted(answer.recommendations, evidence_refs(analysis))


def targeted(
    recommendations: list[_Recommendation], refs: dict[str, tuple[str, str]]
) -> list[Advice]:
    """Each recommendation on the target its reference names, spelt as the evidence spells
    it; one naming no target the evidence has is dropped (F8.11.3)."""
    advice = []
    for r in recommendations:
        found = refs.get(r.target_ref.strip().strip("[]").lower())
        if found is None:
            continue
        kind, name = found
        advice.append(Advice(AdviceTarget(kind), name, r.action, r.rationale, r.reduction_percent))
    return advice
