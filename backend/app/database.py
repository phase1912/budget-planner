"""Database connectivity for the health check (F0.2.3).

Scoped to answering one question — can the service currently reach
PostgreSQL? — not to the request-scoped session repositories will use for
business queries, which is F0.3's engine and connection-pooling concern.
"""

from functools import lru_cache

from fastapi import Depends
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.config import get_settings


@lru_cache
def get_engine() -> AsyncEngine:
    """Build (once) the process-wide engine used for the health check."""
    return create_async_engine(str(get_settings().database_url))


async def check_database_reachable(engine: AsyncEngine = Depends(get_engine)) -> bool:
    """Return whether a trivial query against the database succeeds.

    Never raises: a database outage must degrade the health report, not
    crash the endpoint reporting it.
    """
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return False
    return True
