# ruff: noqa: RUF001 — advice written in Ukrainian on purpose.
"""The advice model is asked from the evidence only, and a failure is not "no advice"."""

import asyncio
from unittest.mock import AsyncMock

import pytest

from app.adapters.advice_generation_agent import (
    AdviceGenerationAdapter,
    _AdviceResponse,
    _Recommendation,
)
from app.agent.core import Agent
from app.domain.advice import Advice, AdviceTarget
from app.domain.goal_analysis import evidence_refs
from app.ports.advice_generation import AdviceUnavailable
from tests.domain.test_advice import ANALYSIS


@pytest.fixture
def agent() -> AsyncMock:
    return AsyncMock(spec=Agent)


def _ref(name: str) -> str:
    """The reference the evidence gives `name`."""
    return next(r for r, (_, n) in evidence_refs(ANALYSIS).items() if n == name)


@pytest.mark.asyncio
async def test_the_model_is_given_the_evidence_in_the_users_currency(agent: AsyncMock) -> None:
    agent.run_structured.return_value = _AdviceResponse(
        recommendations=[
            _Recommendation(
                target_ref=_ref("Cookies Choco 300g"),
                action="Stop buying them",
                rationale="9 of 14 Fresh Market receipts",
                reduction_percent=100,
            )
        ]
    )

    proposed = await AdviceGenerationAdapter(agent).propose(ANALYSIS, "EUR")

    prompt = agent.run_structured.call_args.args[0][0].content[0]["text"]
    assert "on 9 of the 14 receipts from Fresh Market" in prompt
    assert f"[{_ref('Cookies Choco 300g')}] Cookies Choco 300g" in prompt
    assert "61.20 EUR" in prompt
    assert proposed == [
        Advice(
            AdviceTarget.ITEM,
            "Cookies Choco 300g",
            "Stop buying them",
            "9 of 14 Fresh Market receipts",
            100,
        )
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("language", "named", "action"),
    [("uk", "Ukrainian", "Не купуйте їх"), ("pl", "Polish", "Nie kupuj ich")],
)
async def test_advice_in_another_language_keeps_its_target_by_reference(
    agent: AsyncMock, language: str, named: str, action: str
) -> None:
    """F8.11.3: asked in Ukrainian or Polish, the model translated the names it was to copy, and
    every proposal was dropped as naming nothing found — "nothing specific". Named by
    reference, the advice keeps its target as the receipts spell it; a reference to
    nothing is still dropped."""
    agent.run_structured.return_value = _AdviceResponse(
        recommendations=[
            _Recommendation(
                target_ref=f"[{_ref('Cookies Choco 300g')}]",
                action=action,
                rationale="9 / 14 Fresh Market",
                reduction_percent=100,
            ),
            _Recommendation(target_ref="c99", action="—", rationale="—", reduction_percent=50),
        ]
    )

    proposed = await AdviceGenerationAdapter(agent).propose(ANALYSIS, "PLN", language=language)

    prompt = agent.run_structured.call_args.args[0][0].content[0]["text"]
    assert f"Write `action` and `rationale` in {named}" in prompt
    assert "by the reference in brackets" in prompt
    assert [(a.target_kind, a.target_name, a.action) for a in proposed] == [
        (AdviceTarget.ITEM, "Cookies Choco 300g", action)
    ]


@pytest.mark.asyncio
async def test_a_failing_model_is_reported_as_unavailable(agent: AsyncMock) -> None:
    agent.run_structured.side_effect = RuntimeError("API error")

    with pytest.raises(AdviceUnavailable):
        await AdviceGenerationAdapter(agent).propose(ANALYSIS, "PLN")


@pytest.mark.asyncio
async def test_a_model_too_slow_to_answer_is_reported_as_unavailable(agent: AsyncMock) -> None:
    async def hang(*_: object, **__: object) -> None:
        await asyncio.sleep(10)

    agent.run_structured.side_effect = hang

    with pytest.raises(AdviceUnavailable):
        await AdviceGenerationAdapter(agent, timeout_seconds=0.01).propose(ANALYSIS, "PLN")
