import asyncio
import logging

from pydantic import BaseModel, Field

from app.agent.core import Agent
from app.agent.types import Message
from app.domain.advice import Advice, AdviceTarget
from app.domain.goal_analysis import GoalAnalysis, render_advice_context
from app.ports.advice_generation import AdviceGeneratorPort, AdviceUnavailable

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You advise one person on one goal, using only the evidence below, which comes from
their own receipts.

Rules:
- Every recommendation targets exactly one category or one recurring purchase that
  the evidence names, spelt exactly as it is written there. Nothing else.
- Say what to do, concretely: stop, swap, halve, cap at an amount, buy less often.
- Justify it with figures from the evidence: how often, how much, where, the rise.
- Never give general financial tips ("track your spending", "reduce discretionary
  spending", "make a budget"). If the evidence supports nothing specific, return
  no recommendations at all.
- Write amounts in the currency the evidence uses. At most three recommendations,
  the most effective first.
"""


class _Recommendation(BaseModel):
    target_kind: AdviceTarget = Field(
        description="'category' for a spending category, 'item' for a recurring purchase."
    )
    target_name: str = Field(
        description="The category or purchase, exactly as the evidence names it."
    )
    action: str = Field(
        description="What to do, in one short sentence, e.g. 'Stop buying Cola 0.5'."
    )
    rationale: str = Field(description="Why, citing figures from the evidence.")


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

    async def propose(self, analysis: GoalAnalysis, currency: str) -> list[Advice]:
        """Ask the model; see AdviceGeneratorPort.propose. Raises AdviceUnavailable."""
        evidence = render_advice_context(analysis, currency)
        messages = [
            Message(
                role="user",
                content=[{"type": "text", "text": f"{SYSTEM_PROMPT}\nEvidence:\n{evidence}"}],
            )
        ]
        try:
            async with asyncio.timeout(self._timeout_seconds):
                answer = await self._agent.run_structured(
                    messages, schema=_AdviceResponse, temperature=0.0
                )
        except Exception as error:
            logger.exception("Advice generation failed")
            raise AdviceUnavailable from error
        return [
            Advice(r.target_kind, r.target_name, r.action, r.rationale)
            for r in answer.recommendations
        ]
