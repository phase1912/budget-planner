from typing import Protocol

from app.domain.advice import Advice
from app.domain.goal_analysis import GoalAnalysis


class AdviceUnavailable(Exception):
    """No answer could be had from the advice model: failed, timed out or unreadable."""


class AdviceGeneratorPort(Protocol):
    """Proposes recommendations for a goal from the evidence gathered for it (BRD F3)."""

    async def propose(
        self, analysis: GoalAnalysis, currency: str, *, language: str = "en"
    ) -> list[Advice]:
        """Recommendations built only from `analysis`, amounts in `currency`.

        The action and rationale are written in `language` (an ISO 639-1 code the
        product offers, F9.9.5); target names stay as the receipts spell them.

        What comes back is a proposal: the caller keeps only what cites the
        evidence (`app.domain.advice.keep_specific`). Raises AdviceUnavailable
        when no answer could be had, so a failure is never read as "no advice".
        """
        ...
