"""Tests for the uniform error envelope and global exception handlers (F0.2.4).

Every scenario mounts throwaway routes on a fresh app instead of relying on
a real endpoint that raises the exception in question — none exist yet, and
this task is about the envelope every future route gets for free, not any
particular route's behaviour.
"""

from collections.abc import Iterator

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.errors import NotFoundError, PermissionDeniedError
from app.main import create_app


@pytest.fixture
def app() -> Iterator[FastAPI]:
    application = create_app()

    @application.get("/testing/not-found")
    async def raise_not_found() -> None:
        raise NotFoundError("Receipt not found.")

    @application.get("/testing/permission-denied")
    async def raise_permission_denied() -> None:
        raise PermissionDeniedError("You may not edit this budget.")

    @application.get("/testing/http-exception")
    async def raise_http_exception() -> None:
        raise HTTPException(status_code=400, detail="Malformed request.")

    @application.get("/testing/unexpected")
    async def raise_unexpected() -> None:
        raise ValueError("boom")

    @application.get("/testing/validated")
    async def validated(count: int) -> dict[str, int]:
        return {"count": count}

    yield application


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


def test_not_found_error_produces_a_problem_json_response(client: TestClient) -> None:
    response = client.get("/testing/not-found")

    assert response.status_code == 404
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json() == {
        "type": "about:blank",
        "title": "Not Found",
        "status": 404,
        "detail": "Receipt not found.",
        "code": "not_found",
    }


def test_permission_denied_error_produces_a_problem_json_response(client: TestClient) -> None:
    response = client.get("/testing/permission-denied")

    assert response.status_code == 403
    assert response.json()["code"] == "permission_denied"
    assert response.json()["detail"] == "You may not edit this budget."


def test_http_exception_is_wrapped_in_the_same_envelope(client: TestClient) -> None:
    response = client.get("/testing/http-exception")

    assert response.status_code == 400
    assert response.json()["code"] == "bad_request"
    assert response.json()["detail"] == "Malformed request."


def test_unmatched_route_is_wrapped_in_the_same_envelope(client: TestClient) -> None:
    response = client.get("/testing/does-not-exist")

    assert response.status_code == 404
    assert response.json()["code"] == "not_found"


def test_request_validation_error_returns_a_stable_code(client: TestClient) -> None:
    response = client.get("/testing/validated")

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "validation_error"
    assert "count" in body["detail"]


def test_unexpected_exception_returns_a_generic_internal_error(client: TestClient) -> None:
    response = client.get("/testing/unexpected")

    assert response.status_code == 500
    body = response.json()
    assert body == {
        "type": "about:blank",
        "title": "Internal Server Error",
        "status": 500,
        "detail": "An unexpected error occurred.",
        "code": "internal_error",
    }
