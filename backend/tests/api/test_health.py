"""Tests for the health and version endpoints (F0.2.3).

The database dependency is overridden rather than pointed at a real
PostgreSQL instance — these tests assert the endpoint's own behaviour
(status shape, degrade-on-failure), not connectivity to a live database.
"""

from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.health_probe import check_database_reachable
from app.config import Settings, get_settings
from app.main import create_app


@pytest.fixture
def app() -> Iterator[FastAPI]:
    application = create_app()
    yield application
    application.dependency_overrides.clear()


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


def test_health_reports_ok_when_the_database_is_reachable(app: FastAPI, client: TestClient) -> None:
    app.dependency_overrides[check_database_reachable] = lambda: True

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": {"reachable": True}}


def test_health_degrades_without_failing_when_the_database_is_unreachable(
    app: FastAPI, client: TestClient
) -> None:
    app.dependency_overrides[check_database_reachable] = lambda: False

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "degraded", "database": {"reachable": False}}


def test_version_reports_build_sha_and_parser_version(app: FastAPI, client: TestClient) -> None:
    app.dependency_overrides[get_settings] = lambda: Settings(
        _env_file=None,
        database_url="postgresql+asyncpg://user:pass@localhost:5432/db",
        anthropic_api_key="sk-test-key",
        build_sha="abc1234",
    )

    response = client.get("/version")

    assert response.status_code == 200
    assert response.json() == {"build_sha": "abc1234", "parser_version": "1"}
