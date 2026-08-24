"""Request-scoped database session (F0.3.1).

Distinct from `app.database`'s engine, which exists only to answer "is PostgreSQL
reachable?" for the health endpoint. This engine is the one repositories query
and mutate through, sized from settings rather than left at SQLAlchemy's defaults
so pool exhaustion under load is a deliberate capacity choice, not an accident.
"""

from collections.abc import AsyncGenerator
from functools import lru_cache

from fastapi import Depends
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings


@lru_cache
def get_engine() -> AsyncEngine:
    """Build (once) the process-wide engine backing every request-scoped session."""
    settings = get_settings()
    return create_async_engine(
        str(settings.database_url),
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        pool_pre_ping=True,
    )


@lru_cache
def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Build (once) the factory `get_db_session` uses to open one session per request."""
    return async_sessionmaker(get_engine(), expire_on_commit=False)


async def get_db_session(
    session_factory: async_sessionmaker[AsyncSession] = Depends(get_session_factory),
) -> AsyncGenerator[AsyncSession, None]:
    """Yield one session per request: commit if the route completes, roll back if it raises.

    This is the Unit of Work boundary — a route handler's whole chain of repository
    calls shares one transaction, committed only if every step in it succeeded, so a
    failure partway through a multi-step mutation can never leave the database in a
    half-written state.
    """
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
