"""Keeping what every model call cost (F21.9.1, ADR-0030).

The agent hands each call's `Spend` here. It is written in a session of its own and
committed at once: the call cost money whatever becomes of the request around it — a
refused card, a failed parse, a job that runs after its response — so its record must not
roll back with it.
"""

import logging

from app.agent.metering import Spend
from app.db.session import get_session_factory
from app.models.ai_usage import AiUsage

logger = logging.getLogger(__name__)


async def record_usage(spend: Spend) -> None:
    """Write `spend` as one row; a failure is logged, never raised into the call."""
    try:
        async with get_session_factory()() as session:
            session.add(
                AiUsage(
                    user_id=spend.user_id,
                    purpose=spend.purpose,
                    model=spend.model,
                    input_tokens=spend.input_tokens,
                    output_tokens=spend.output_tokens,
                    audio_seconds=spend.audio_seconds,
                    credits=spend.credits,
                    charged=spend.charged,
                )
            )
            await session.commit()
    except Exception:
        logger.exception("Recording a model call's cost failed (%s)", spend.purpose)
