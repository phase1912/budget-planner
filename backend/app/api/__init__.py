"""Registry feature epics append their router to, and nothing else (F0.2.1).

`create_app()` mounts every router in `ROUTERS` once, at startup. A feature epic
that adds an endpoint adds its router to this list; it never touches `create_app()`
or wires anything itself.
"""

from fastapi import APIRouter, FastAPI

from app.api.auth import router as auth_router
from app.api.health import router as health_router

ROUTERS: list[APIRouter] = [health_router, auth_router]


def include_routers(app: FastAPI) -> None:
    """Mount every router in `ROUTERS` onto `app`."""
    for router in ROUTERS:
        app.include_router(router)
