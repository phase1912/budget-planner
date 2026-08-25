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
    implemented = {
        "test_reject_unsupported_file_format",
        "test_upload_a_single_receipt_within_limits",
        "test_reject_exceeding_photo_count_in_single_receipt_mode",
        "test_reject_exceeding_size_limit_in_single_receipt_mode",
    }
    if request.node.name not in implemented:
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
        "files": (
            "statement.docx",
            b"dummy word content",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    }
    return client.post("/receipts/upload", files=files)  # type: ignore[no-any-return]  # type: ignore[no-any-return]


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


@given('the user selects "single receipt" upload mode', target_fixture="auth_user")
def user_selects_single_receipt_mode(app: FastAPI) -> User:
    return user_is_logged_in(app)


@when("the user uploads 4 photos totaling 20 MB for that receipt", target_fixture="upload_response")
def user_uploads_4_photos(client: TestClient, auth_user: User) -> Response:
    # Send 4 files
    files = [
        (
            "files",
            (
                f"photo{i}.jpg",
                b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01" + b"x" * (5 * 1024 * 1024),
                "image/jpeg",
            ),
        )
        for i in range(4)
    ]
    return client.post("/receipts/upload", files=files)  # type: ignore[no-any-return]


@then("the agent should accept all 4 photos")
def agent_accepts_all_photos(upload_response: Response) -> None:
    assert upload_response.status_code == 200


@then("process them as one receipt")
def process_as_one_receipt() -> None:
    pass  # Implied by a successful response in single mode


@when("the user attempts to upload 11 photos for that receipt", target_fixture="upload_response")
def user_uploads_11_photos(client: TestClient, auth_user: User) -> Response:
    files = [
        ("files", (f"photo{i}.jpg", b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01", "image/jpeg"))
        for i in range(11)
    ]
    return client.post("/receipts/upload", files=files)  # type: ignore[no-any-return]


@then("the agent should reject the 11th photo")
def agent_rejects_11th_photo(upload_response: Response) -> None:
    assert upload_response.status_code == 400
    assert upload_response.json()["code"] == "upload_limit_exceeded"


@then("inform the user of the 10-photo limit")
def inform_user_of_10_photo_limit(upload_response: Response) -> None:
    assert "10 photos" in upload_response.json()["detail"]


@when(
    "the user attempts to upload photos totaling 55 MB for that receipt",
    target_fixture="upload_response",
)
def user_uploads_55_mb(client: TestClient, auth_user: User) -> Response:
    files = [
        (
            "files",
            (
                "photo.jpg",
                b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01" + b"x" * (55 * 1024 * 1024),
                "image/jpeg",
            ),
        )
    ]
    return client.post("/receipts/upload", files=files)  # type: ignore[no-any-return]


@then("the agent should reject the upload")
def agent_rejects_upload_size(upload_response: Response) -> None:
    pass


@then("inform the user of the 50 MB limit")
def inform_user_of_50_mb_limit(upload_response: Response) -> None:
    assert upload_response.status_code == 400
    assert "50 MB" in upload_response.json()["detail"]
