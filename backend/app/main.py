"""Application factory (F0.2.1).

The single place the FastAPI service is assembled. Feature epics register
themselves through `app.api.ROUTERS`; nothing here should need to change as
routers, or later middleware, are added.
"""

import asyncio
import logging
from collections.abc import AsyncGenerator, Awaitable
from contextlib import asynccontextmanager, suppress
from datetime import UTC, date, datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.adapters.advice_generation_agent import AdviceGenerationAdapter
from app.agent.factory import agent_from_settings
from app.api import include_routers
from app.api.errors import register_exception_handlers
from app.api.rate_limit import limiter
from app.core.config import get_settings
from app.db.session import get_session_factory
from app.services.activity import ActivityService
from app.services.job_recovery import fail_orphaned_upload_jobs
from app.services.proactive_advice import prepare_advice_for_everyone, run_every

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Clear upload jobs the previous process left mid-flight, prune old activity, then serve.

    Instances start often — the service scales to zero — so pruning at start keeps the
    activity log within its 12 months (ADR-0020) without a scheduler of its own.

    While serving, the proactive advice pass (BRD F7) runs on its schedule, and
    stops with the app.

    Only clearing orphaned jobs runs before serving: done later, it could fail an upload
    begun on this very instance. Loading the model client and pruning go on in the
    background, so the instance answers its startup probe at once — waited for, they
    pushed the start past Cloud Run's probe and failed deploys.
    """
    session_factory = get_session_factory()
    async with session_factory() as session:
        await fail_orphaned_upload_jobs(session)
    housekeeping = asyncio.create_task(_housekeeping())
    schedule = _start_proactive_advice()
    yield
    for task in (housekeeping, schedule):
        if task is not None:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task


async def _housekeeping() -> None:
    """What a start needs done but nobody waits for: the model client loaded off the event
    loop, and old activity pruned."""
    await asyncio.to_thread(_warm_model_client)
    await _prune_activity()


def _warm_model_client() -> None:
    """Load the model client while the instance starts, not inside the first upload.

    Importing litellm takes seconds on one vCPU and holds the event loop while it runs;
    done lazily, it froze every request — the upload's own progress polls included —
    for 11-14 s on the first receipt read by each new instance. Never stops a start.
    """
    try:
        import litellm  # noqa: F401
    except Exception:
        logger.exception("The model client could not be loaded at start")


async def _prune_activity() -> None:
    """Drop activity past its 12 months (ADR-0020); housekeeping that never stops a start."""
    try:
        async with get_session_factory()() as session:
            await ActivityService(session).prune(datetime.now(UTC))
            await session.commit()
    except Exception:
        logger.exception("Old activity was not pruned at start")


def _start_proactive_advice() -> "asyncio.Task[None] | None":
    """Start the background pass that readies advice for goals at risk, unless turned off."""
    settings = get_settings()
    if settings.proactive_advice_interval_minutes <= 0:
        return None
    generator = AdviceGenerationAdapter(agent_from_settings())

    def one_pass(as_of: date) -> Awaitable[int]:
        return prepare_advice_for_everyone(
            get_session_factory(),
            generator,
            as_of,
            required_receipts=settings.min_receipts_for_advice,
            required_days=settings.min_history_days_for_advice,
        )

    return asyncio.create_task(
        run_every(
            settings.proactive_advice_interval_minutes * 60,
            one_pass,
            first_delay_seconds=60,
        )
    )


def create_app() -> FastAPI:
    """Build and wire a fresh FastAPI application instance."""
    app = FastAPI(title="AI Budget Agent", lifespan=lifespan)
    app.state.limiter = limiter

    settings = get_settings()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from app.api.middleware import UserContextMiddleware

    app.add_middleware(UserContextMiddleware)

    register_exception_handlers(app)
    include_routers(app)
    return app


app = create_app()
