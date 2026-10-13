"""The model is asked about ambiguous names only, and its answer is kept to what was offered."""

from unittest.mock import AsyncMock

import pytest

from app.adapters.product_matching_agent import ProductMatchingAdapter, _Answer, _Answers
from app.agent.core import Agent
from app.ports.product_matching import MatchQuestion

QUESTION = MatchQuestion("JajkoNiesMeltie20g", {"1": "Jajko Niespodzianka 20g"})


@pytest.mark.asyncio
async def test_an_offered_candidate_is_kept_and_anything_else_is_none() -> None:
    agent = AsyncMock(spec=Agent)
    agent.run_structured.return_value = _Answers(
        answers=[
            _Answer(name="JajkoNiesMeltie20g", candidate="1"),
            _Answer(name="Never asked", candidate="1"),
        ]
    )
    other = MatchQuestion("Chleb 300g", {"1": "Chleb Firmowy 300g"})
    agent.run_structured.return_value.answers.append(_Answer(name="Chleb 300g", candidate="7"))

    answers = await ProductMatchingAdapter(agent).match([QUESTION, other])

    assert answers == {"JajkoNiesMeltie20g": "1", "Chleb 300g": None}
    prompt = agent.run_structured.call_args.args[0][0].content[0]["text"]
    assert "Jajko Niespodzianka 20g" in prompt


@pytest.mark.asyncio
async def test_a_failing_model_leaves_every_name_unmatched() -> None:
    agent = AsyncMock(spec=Agent)
    agent.run_structured.side_effect = RuntimeError("API error")

    assert await ProductMatchingAdapter(agent).match([QUESTION]) == {"JajkoNiesMeltie20g": None}
