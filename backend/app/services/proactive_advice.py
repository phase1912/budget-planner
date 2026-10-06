"""Advice waiting on goals at risk before the user asks (BRD F7 — F8.8).

A scheduled pass over every user: each goal heading over its cap with no advice
from this month gets some, so when the user next opens the app the warning is
already there, and so is a way to correct course. The warning itself is worked
out live from the month's pace (`app.domain.goal_pace`); only the advice is made
here, because only the advice needs the model.
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.context import current_user_id
from app.models.user import User
from app.ports.advice_generation import AdviceGeneratorPort
from app.services.advice import build_advice_service

logger = logging.getLogger(__name__)


async def prepare_advice_for_everyone(
    session_factory: async_sessionmaker[AsyncSession],
    generator: AdviceGeneratorPort,
    as_of: date,
    *,
    required_receipts: int,
    required_days: int,
) -> int:
    """One pass: advice for every user's goals at risk on `as_of`; returns how many goals got some.

    Each user runs in their own session and ownership context (N2), and one user's
    failure is logged rather than stopping the others.
    """
    async with session_factory() as session:
        users = (await session.execute(select(User.id, User.currency))).all()

    prepared = 0
    for user_id, currency in users:
        token = current_user_id.set(user_id)
        try:
            async with session_factory() as session:
                service = build_advice_service(
                    session,
                    generator,
                    required_receipts=required_receipts,
                    required_days=required_days,
                )
                prepared += await service.prepare_for_goals_at_risk(as_of, currency)
                await session.commit()
        except Exception:
            logger.exception("Preparing advice for user %s failed", user_id)
        finally:
            current_user_id.reset(token)
    return prepared


async def run_every(
    interval_seconds: float,
    one_pass: Callable[[date], Awaitable[int]],
    *,
    first_delay_seconds: float,
) -> None:
    """Run `one_pass` for today after `first_delay_seconds`, then every `interval_seconds`.

    Runs until cancelled, which is how the app stops it on shutdown. A failed
    pass is logged and the schedule carries on.
    """
    await asyncio.sleep(first_delay_seconds)
    while True:
        try:
            prepared = await one_pass(datetime.now(UTC).date())
            logger.info("Proactive advice pass prepared advice for %s goals", prepared)
        except Exception:
            logger.exception("Proactive advice pass failed")
        await asyncio.sleep(interval_seconds)
