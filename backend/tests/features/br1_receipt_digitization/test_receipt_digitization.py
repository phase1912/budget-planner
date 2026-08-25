"""Runs BR-1's Gherkin scenarios (F0.6.2)."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import Response
from pytest import FixtureRequest
from pytest_bdd import given, scenarios, then, when

from app.api.dependencies import get_current_user
from app.main import create_app
from app.models.user import User

scenarios("receipt_digitization.feature")


@pytest.fixture(autouse=True)
def skip_unimplemented(request: FixtureRequest) -> None:
    if request.node.name != "test_reject_unsupported_file_format":
        pytest.skip("Awaiting further F2.x implementations")


@pytest.fixture
def app() -> FastAPI:
    return create_app()


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


@given("the user is logged in", target_fixture="auth_user")
def user_is_logged_in(app: FastAPI) -> User:
    user = User(
        id="usr_test123",
        email="test@test.com",
        first_name="T",
        last_name="T",
        password_hash="x",
    )
    app.dependency_overrides[get_current_user] = lambda: user
    return user


@when('the user submits a ".docx" file instead of a photo', target_fixture="upload_response")
def user_submits_docx(client: TestClient) -> Response:
    files = {
        "file": (
            "statement.docx",
            b"dummy word content",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    }
    return client.post("/receipts/upload", files=files)  # type: ignore[no-any-return]


@then("the agent should reject the upload")
def agent_rejects_upload(upload_response: Response) -> None:
    assert upload_response.status_code == 415


@then(
    "the agent should return an error stating supported formats are JPEG, PNG, HEIC, and PDF-scan"
)
def agent_returns_error(upload_response: Response) -> None:
    data = upload_response.json()
    assert data["code"] == "unsupported_media_type"
    assert "JPEG, PNG, HEIC or a PDF scan" in data["detail"]
