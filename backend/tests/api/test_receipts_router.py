import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.dependencies import get_current_user, get_storage_service
from app.main import create_app
from app.models.user import User
from app.ports.storage import StoragePort


class MockStoragePort(StoragePort):
    async def upload_file(
        self,
        object_name: str,
        content: bytes,
        content_type: str,
        metadata: dict[str, str] | None = None,
    ) -> str:
        return object_name.split("/")[-1]

    async def get_object_metadata(self, object_name: str) -> dict[str, str]:
        # Return ownership for user id "user-a-id" only if it matches
        parts = object_name.split("/")
        user_id = parts[1]
        file_id = parts[2]
        if user_id == "user-a-id" and file_id == "valid-file":
            return {"owner_id": "user-a-id"}
        from app.services.storage import ObjectNotFoundError

        raise ObjectNotFoundError()

    async def generate_presigned_url(self, object_name: str, expiration_seconds: int = 3600) -> str:
        return f"https://mock-s3.local/{object_name}"


@pytest.fixture
def app() -> FastAPI:
    app = create_app()
    app.dependency_overrides[get_storage_service] = lambda: MockStoragePort()
    return app


def test_cross_user_access_returns_404(app: FastAPI) -> None:
    user_a = User(id="user-a-id", email="a@test.com")
    user_b = User(id="user-b-id", email="b@test.com")

    # Authenticate as user B
    app.dependency_overrides[get_current_user] = lambda: user_b

    client = TestClient(app, follow_redirects=False)
    # User B tries to access User A's valid file
    response = client.get("/receipts/images/valid-file")
    assert response.status_code == 404
    assert response.json()["code"] == "not_found"

    # Authenticate as user A
    app.dependency_overrides[get_current_user] = lambda: user_a
    # User A accesses their own file
    response = client.get("/receipts/images/valid-file")
    # Redirect implies success (302)
    # TestClient follows redirects by default? Let's check status.
    assert response.status_code in (
        302,
        307,
    )  # because httpx follows redirect? Wait. Let's disable redirects.


def test_owner_access_redirects(app: FastAPI) -> None:
    user_a = User(id="user-a-id", email="a@test.com")
    app.dependency_overrides[get_current_user] = lambda: user_a
    client = TestClient(app, follow_redirects=False)

    response = client.get("/receipts/images/valid-file")
    assert (
        response.status_code == 307 or response.status_code == 302
    )  # FastAPI RedirectResponse is 307?
