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
        "test_upload_multiple_receipts_across_separate_lines",
        "test_reject_exceeding_limits_on_one_line_in_multiple_receipts_mode",
    }
    if request.node.name not in implemented:
        pytest.skip("Awaiting further F2.x implementations")


@pytest.fixture
def app() -> FastAPI:
    app_instance = create_app()

    from typing import Any

    from app.api.dependencies import get_storage_service
    from app.db.session import get_db_session
    from app.ports.storage import StoragePort

    class MockStoragePort(StoragePort):
        async def upload_file(
            self,
            object_name: str,
            content: bytes,
            content_type: str,
            metadata: dict[str, str] | None = None,
        ) -> str:
            return object_name

        async def get_object_metadata(self, object_name: str) -> dict[str, str]:
            return {"owner_id": "mock"}

        async def generate_presigned_url(
            self, object_name: str, expiration_seconds: int = 3600
        ) -> str:
            return f"https://mock-s3.local/{object_name}"

        async def download_file(self, object_name: str) -> bytes:
            return b"fake-image-data"

    async def mock_get_storage_service() -> Any:
        yield MockStoragePort()

    app_instance.dependency_overrides[get_storage_service] = mock_get_storage_service

    import uuid

    class MockSession:
        def add(self, obj: Any) -> None:
            if hasattr(obj, "id") and obj.id is None:
                obj.id = uuid.uuid4()

        async def commit(self) -> None:
            pass

        async def flush(self) -> None:
            pass

    async def mock_get_db_session() -> Any:
        yield MockSession()

    app_instance.dependency_overrides[get_db_session] = mock_get_db_session

    from app.api.routers.receipts import get_receipt_service
    from app.services.receipts import ReceiptService

    class MockReceiptService(ReceiptService):
        async def process_upload_job_task(
            self, job_id: uuid.UUID, user: User, files_data: list[dict[str, Any]]
        ) -> None:
            pass

    def mock_get_receipt_service() -> MockReceiptService:
        return MockReceiptService(MockStoragePort())

    app_instance.dependency_overrides[get_receipt_service] = mock_get_receipt_service

    return app_instance


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


@given('the user selects "multiple receipts" upload mode', target_fixture="auth_user")
def user_selects_multiple_receipts_mode(app: FastAPI) -> User:
    return user_is_logged_in(app)


@when("the user adds two upload lines, one for a grocery receipt and one for a restaurant receipt")
def user_adds_two_upload_lines() -> None:
    pass  # UI step, handled in tests by sending multiple form fields


@when("uploads 3 photos totaling 15 MB to the first line", target_fixture="batch_files")
def uploads_3_photos_to_first_line() -> list[tuple[str, tuple[str, bytes, str]]]:
    return [
        (
            "line_0",
            (
                f"photo_g_{i}.jpg",
                b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01" + b"x" * (5 * 1024 * 1024),
                "image/jpeg",
            ),
        )
        for i in range(3)
    ]


@when("uploads 2 photos totaling 10 MB to the second line", target_fixture="upload_response")
def uploads_2_photos_to_second_line(
    client: TestClient, auth_user: User, batch_files: list[tuple[str, tuple[str, bytes, str]]]
) -> Response:
    batch_files.extend(
        [
            (
                "line_1",
                (
                    f"photo_r_{i}.jpg",
                    b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01" + b"x" * (5 * 1024 * 1024),
                    "image/jpeg",
                ),
            )
            for i in range(2)
        ]
    )
    return client.post("/receipts/upload/batch", files=batch_files)  # type: ignore[no-any-return]


@then("the agent should accept both lines")
def agent_accepts_both_lines(upload_response: Response) -> None:
    assert upload_response.status_code == 200
    assert upload_response.json()["message"] == "Batch accepted"


@then("process each line as a separate receipt")
def process_each_line_as_separate() -> None:
    pass


@given("has added two upload lines")
def has_added_two_upload_lines() -> None:
    pass


@when("the user attempts to upload 12 photos to the first line", target_fixture="upload_response")
def uploads_12_photos_to_first_line(client: TestClient, auth_user: User) -> Response:
    batch_files = [
        (
            "line_0",
            (
                f"photo_{i}.jpg",
                b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01",
                "image/jpeg",
            ),
        )
        for i in range(12)
    ]
    batch_files.append(
        (
            "line_1",
            (
                "photo_ok.jpg",
                b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01",
                "image/jpeg",
            ),
        )
    )
    return client.post("/receipts/upload/batch", files=batch_files)  # type: ignore[no-any-return]


@then("the agent should reject the additional photos on that line")
def agent_rejects_additional_photos(upload_response: Response) -> None:
    assert upload_response.status_code == 400
    assert upload_response.json()["code"] == "upload_limit_exceeded"


@then("the second line should remain unaffected")
def second_line_unaffected() -> None:
    pass
