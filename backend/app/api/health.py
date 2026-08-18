"""Liveness and version reporting (F0.2.3).

Operational endpoints, not business behaviour — used by orchestration to
know the process is alive and reachable, and by whoever is debugging a
deployment to know exactly what code and parser version it is running.
"""

from fastapi import APIRouter, Depends

from app.config import Settings, get_settings
from app.database import check_database_reachable
from app.parsing import CURRENT_PARSER_VERSION

router = APIRouter()


@router.get("/health")
async def health(db_reachable: bool = Depends(check_database_reachable)) -> dict[str, object]:
    """Report process liveness and database reachability.

    Always 200: the process being able to respond at all is the liveness
    signal. `database.reachable` carries dependency health as data instead
    of conflating a downstream outage with the process itself being down.
    """
    return {
        "status": "ok" if db_reachable else "degraded",
        "database": {"reachable": db_reachable},
    }


@router.get("/version")
async def version(settings: Settings = Depends(get_settings)) -> dict[str, str]:
    """Report the running build SHA and current receipt parser version (BRD A15)."""
    return {
        "build_sha": settings.build_sha,
        "parser_version": CURRENT_PARSER_VERSION,
    }
