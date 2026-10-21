"""Tests for the application factory and router registration (F0.2.1).

No business behaviour is asserted here — there is none yet. These guard the one
thing this task delivers: `create_app()` produces a working FastAPI instance, and
a router added to `app.api.ROUTERS` is actually mounted, so a feature epic that
follows this convention can trust it works without re-deriving it from the code.
"""

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from app import api as api_module
from app.api import include_routers
from app.main import create_app


def test_create_app_returns_a_fastapi_instance() -> None:
    app = create_app()

    assert isinstance(app, FastAPI)
    assert app.title == "AI Budget Agent"


def test_module_level_app_is_ready_to_serve() -> None:
    from app.main import app as module_app

    assert isinstance(module_app, FastAPI)


def test_include_routers_mounts_every_router_registered_in_routers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    probe_router = APIRouter()

    @probe_router.get("/probe")
    def probe() -> dict[str, bool]:
        return {"ok": True}

    monkeypatch.setattr(api_module, "ROUTERS", [probe_router])

    app = FastAPI()
    include_routers(app)
    response = TestClient(app).get("/probe")

    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_include_routers_mounts_nothing_when_routers_is_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(api_module, "ROUTERS", [])

    baseline_paths = [route.path for route in FastAPI().routes if hasattr(route, "path")]
    app = FastAPI()
    include_routers(app)
    app_paths = [route.path for route in app.routes if hasattr(route, "path")]

    assert app_paths == baseline_paths


@pytest.mark.asyncio
async def test_a_start_serves_before_the_slow_housekeeping_is_done(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Waiting for the model client and pruning pushed starts past Cloud Run's probe."""
    import asyncio

    from app import main

    finished: list[str] = []

    async def no_orphans(session: object) -> None:
        finished.append("orphans")

    async def slow_housekeeping() -> None:
        await asyncio.sleep(3600)
        finished.append("housekeeping")

    monkeypatch.setattr(main, "fail_orphaned_upload_jobs", no_orphans)
    monkeypatch.setattr(main, "_housekeeping", slow_housekeeping)
    monkeypatch.setattr(main, "_start_proactive_advice", lambda: None)

    async with asyncio.timeout(5), main.lifespan(main.create_app()):
        assert finished == ["orphans"]
