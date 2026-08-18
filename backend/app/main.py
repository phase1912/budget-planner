"""Application factory (F0.2.1).

The single place the FastAPI service is assembled. Feature epics register
themselves through `app.api.ROUTERS`; nothing here should need to change as
routers, and later middleware and exception handlers, are added.
"""

from fastapi import FastAPI

from app.api import include_routers


def create_app() -> FastAPI:
    """Build and wire a fresh FastAPI application instance."""
    app = FastAPI(title="AI Budget Agent")
    include_routers(app)
    return app


app = create_app()
