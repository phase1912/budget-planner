"""Application factory (F0.2.1).

The single place the FastAPI service is assembled. Feature epics register
themselves through `app.api.ROUTERS`; nothing here should need to change as
routers, or later middleware, are added.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api import include_routers
from app.api.errors import register_exception_handlers
from app.api.rate_limit import limiter
from app.core.config import get_settings
from app.db.session import get_session_factory
from app.services.job_recovery import fail_orphaned_upload_jobs


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Clear upload jobs the previous process left mid-flight before serving."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        await fail_orphaned_upload_jobs(session)
    yield


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
