"""What every model call cost, and whose it was (F21.9.1)."""

import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agent.core import Agent
from app.agent.metering import Purpose, charge_to, credits_of, spend, unasked
from app.agent.types import Message
from app.core.context import current_user_id


def test_a_credit_is_a_tenth_of_a_cent() -> None:
    assert credits_of(0.0005683) == Decimal("0.568")
    assert credits_of(Decimal("0.016")) == Decimal("16.000")


def test_the_signed_in_user_pays_and_a_job_names_its_own_payer() -> None:
    me, them = uuid.uuid4(), uuid.uuid4()
    token = current_user_id.set(me)
    try:
        asked = spend(Purpose.ASSISTANT, "m", 0.004)
        with charge_to(them):
            in_job = spend(Purpose.RECEIPT, "m", 0.01)
    finally:
        current_user_id.reset(token)

    assert (asked.user_id, asked.charged, asked.credits) == (me, True, Decimal("4.000"))
    assert (in_job.user_id, in_job.charged) == (them, True)


def test_work_nobody_asked_for_is_recorded_but_charged_to_no_one() -> None:
    me = uuid.uuid4()
    with charge_to(me):
        with unasked():
            proactive = spend(Purpose.ADVICE, "m", 0.003)
        matching = spend(Purpose.PRODUCTS, "m", 0.002)
    nobody = spend(Purpose.RECEIPT, "m", 0.01)

    assert (proactive.user_id, proactive.charged) == (me, False)
    assert (matching.charged, nobody.charged, nobody.user_id) == (False, False, None)


@pytest.mark.asyncio
@patch("litellm.acompletion")
async def test_every_call_hands_its_real_cost_and_purpose_to_the_recorder(
    mock_acompletion: MagicMock,
) -> None:
    recorder = AsyncMock()
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = "hi"
    response._hidden_params = {"response_cost": 0.0012}
    response.usage.prompt_tokens, response.usage.completion_tokens = 300, 150
    mock_acompletion.return_value = response
    agent = Agent(model="vertex_ai/gemini-2.5-flash", recorder=recorder)

    await agent.run([Message(role="user", content="hello")], purpose=Purpose.GOAL_MAPPING)

    [recorded] = [c.args[0] for c in recorder.await_args_list]
    assert (recorded.purpose, recorded.credits) == (Purpose.GOAL_MAPPING, Decimal("1.200"))
    assert (recorded.input_tokens, recorded.output_tokens) == (300, 150)
