"""Application factory (F0.2.1).

The single place the FastAPI service is assembled. Feature epics register
themselves through `app.api.ROUTERS`; nothing here should need to change as
routers, or later middleware, are added.
"""

import asyncio
from collections.abc import AsyncGenerator, Awaitable
from contextlib import asynccontextmanager, suppress
from datetime import date

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.adapters.advice_generation_agent import AdviceGenerationAdapter
from app.agent.factory import agent_from_settings
from app.api import include_routers
from app.api.errors import register_exception_handlers
from app.api.rate_limit import limiter
from app.core.config import get_settings
from app.db.session import get_session_factory
from app.services.job_recovery import fail_orphaned_upload_jobs
from app.services.proactive_advice import prepare_advice_for_everyone, run_every


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Clear upload jobs the previous process left mid-flight, then serve.

    While serving, the proactive advice pass (BRD F7) runs on its schedule, and
    stops with the app.
    """
    session_factory = get_session_factory()
    async with session_factory() as session:
        await fail_orphaned_upload_jobs(session)
    schedule = _start_proactive_advice()
    yield
    if schedule is not None:
        schedule.cancel()
        with suppress(asyncio.CancelledError):
            await schedule


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
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

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
