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
from app.ports.advice_generation import AdviceUnavailable
from tests.domain.test_advice import ANALYSIS


@pytest.fixture
def agent() -> AsyncMock:
    return AsyncMock(spec=Agent)


@pytest.mark.asyncio
async def test_the_model_is_given_the_evidence_in_the_users_currency(agent: AsyncMock) -> None:
    agent.run_structured.return_value = _AdviceResponse(
        recommendations=[
            _Recommendation(
                target_kind=AdviceTarget.ITEM,
                target_name="Cookies Choco 300g",
                action="Stop buying them",
                rationale="9 of 14 Fresh Market receipts",
                reduction_percent=100,
            )
        ]
    )

    proposed = await AdviceGenerationAdapter(agent).propose(ANALYSIS, "EUR")

    prompt = agent.run_structured.call_args.args[0][0].content[0]["text"]
    assert "on 9 of the 14 receipts from Fresh Market" in prompt
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
