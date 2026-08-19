"""Application factory (F0.2.1).

The single place the FastAPI service is assembled. Feature epics register
themselves through `app.api.ROUTERS`; nothing here should need to change as
routers, or later middleware, are added.
"""

from fastapi import FastAPI

from app.api import include_routers
from app.errors import register_exception_handlers


def create_app() -> FastAPI:
    """Build and wire a fresh FastAPI application instance."""
    app = FastAPI(title="AI Budget Agent")
    register_exception_handlers(app)
    include_routers(app)
    return app


app = create_app()
