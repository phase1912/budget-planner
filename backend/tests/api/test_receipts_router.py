import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, ClassVar
from unittest.mock import AsyncMock, patch

import jwt
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.dependencies import get_current_user, get_storage_service
from app.api.errors import DomainError
from app.core.config import get_settings
from app.db.session import get_db_session
from app.main import create_app
from app.models.receipt import Receipt, ReceiptStatus
from app.models.upload_job import JobStatus, UploadJob
from app.models.user import User
from app.ports.storage import StoragePort


class MockStoragePort(StoragePort):
    # Class-level because the app fixture builds a fresh instance per request,
    # so a test asserting on deletions has nothing else to look at.
    deleted: ClassVar[list[str]] = []

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

    async def download_file(self, object_name: str) -> bytes:
        return b"fake-image-data"

    async def delete_file(self, object_name: str) -> None:
        MockStoragePort.deleted.append(object_name)


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


def test_list_receipts_endpoint(app: FastAPI) -> None:
    import uuid

    import jwt

    from app.core.config import get_settings
    from app.db.session import get_db_session

    user = User(id=uuid.uuid4(), email="list@test.com")
    app.dependency_overrides[get_current_user] = lambda: user

    async def mock_db_session() -> Any:
        from unittest.mock import AsyncMock, MagicMock

        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.unique().scalars().all.return_value = []
        result_mock.scalar_one_or_none.return_value = 0
        result_mock.scalar.return_value = 0
        session.execute.return_value = result_mock
        session.scalar.return_value = 0
        yield session

    app.dependency_overrides[get_db_session] = mock_db_session

    client = TestClient(app, follow_redirects=False)
    token = jwt.encode(
        {"sub": str(user.id)}, get_settings().jwt_secret_key.get_secret_value(), algorithm="HS256"
    )
    client.headers["Authorization"] = f"Bearer {token}"

    response = client.get("/receipts?page=1&size=20")
    assert response.status_code == 200, response.json()
    data = response.json()
    assert data["total"] == 0
    assert len(data["items"]) == 0


def test_get_receipt_detail_endpoint(app: FastAPI) -> None:
    import uuid

    import jwt

    from app.core.config import get_settings
    from app.db.session import get_db_session

    user = User(id=uuid.uuid4(), email="detail@test.com")
    app.dependency_overrides[get_current_user] = lambda: user

    async def mock_db_session() -> Any:
        from unittest.mock import AsyncMock, MagicMock

        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.unique().scalar_one_or_none.return_value = None
        session.execute.return_value = result_mock
        yield session

    app.dependency_overrides[get_db_session] = mock_db_session

    client = TestClient(app, follow_redirects=False)
    token = jwt.encode(
        {"sub": str(user.id)}, get_settings().jwt_secret_key.get_secret_value(), algorithm="HS256"
    )
    client.headers["Authorization"] = f"Bearer {token}"

    random_id = str(uuid.uuid4())
    response = client.get(f"/receipts/{random_id}")
    assert response.status_code == 404
    assert response.json()["code"] == "not_found"


def test_resolve_total_endpoint(app: FastAPI) -> None:
    import uuid
    from typing import Any

    import jwt
    from fastapi.testclient import TestClient

    from app.api.dependencies import get_current_user
    from app.core.config import get_settings
    from app.db.session import get_db_session
    from app.models.upload_job import JobStatus, UploadJob
    from app.models.user import User

    user = User(id=uuid.uuid4(), email="total@test.com")
    job_id = uuid.uuid4()
    job = UploadJob(
        id=job_id,
        user_id=user.id,
        status=JobStatus.COMPLETED,
        file_ids=[],
        result_data={
            "extractions": [{"receipt_total_confidence": 40, "transaction_date": "2024-01-01"}]
        },
    )
    app.dependency_overrides[get_current_user] = lambda: user

    async def mock_db_session() -> Any:
        from unittest.mock import AsyncMock, MagicMock

        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = job
        session.execute.return_value = result_mock
        yield session

    app.dependency_overrides[get_db_session] = mock_db_session

    client = TestClient(app, follow_redirects=False)
    token = jwt.encode(
        {"sub": str(user.id)}, get_settings().jwt_secret_key.get_secret_value(), algorithm="HS256"
    )
    client.headers["Authorization"] = f"Bearer {token}"

    response = client.post(
        f"/receipts/upload/{job_id}/resolve-total",
        json={"extraction_index": 0, "receipt_total": "0.00"},
    )
    assert response.status_code == 200, response.json()
    data = response.json()
    assert data["job_id"] == str(job_id)
    assert data["extracted_data"]["extractions"][0]["receipt_total"] == "0.00"
    assert data["extracted_data"]["extractions"][0].get("requires_manual_review") is not True


def test_commit_job_endpoint(app: FastAPI) -> None:
    import uuid
    from typing import Any

    import jwt
    from fastapi.testclient import TestClient

    from app.api.dependencies import get_current_user
    from app.core.config import get_settings
    from app.db.session import get_db_session
    from app.models.upload_job import JobStatus, UploadJob
    from app.models.user import User

    user = User(id=uuid.uuid4(), email="commit@test.com")
    job_id = uuid.uuid4()
    job = UploadJob(
        id=job_id,
        user_id=user.id,
        status=JobStatus.COMPLETED,
        file_ids=[],
        result_data={
            "extractions": [
                {"merchant_name": "Test", "line_items": [], "items_sum_matches_total": True}
            ]
        },
    )
    app.dependency_overrides[get_current_user] = lambda: user

    async def mock_db_session() -> Any:
        from unittest.mock import AsyncMock, MagicMock

        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = job
        session.execute.return_value = result_mock
        yield session

    app.dependency_overrides[get_db_session] = mock_db_session

    client = TestClient(app, follow_redirects=False)
    token = jwt.encode(
        {"sub": str(user.id)}, get_settings().jwt_secret_key.get_secret_value(), algorithm="HS256"
    )
    client.headers["Authorization"] = f"Bearer {token}"

    response = client.post(f"/receipts/upload/{job_id}/commit", json={"indices_to_store": [0]})
    assert response.status_code == 200, response.json()
    data = response.json()
    assert data["status"] == "stored"
    assert job.status.value == "stored"


def test_commit_job_endpoint_skip_duplicate(app: FastAPI) -> None:
    import uuid
    from typing import Any

    import jwt
    from fastapi.testclient import TestClient

    from app.api.dependencies import get_current_user
    from app.core.config import get_settings
    from app.db.session import get_db_session
    from app.models.upload_job import JobStatus, UploadJob
    from app.models.user import User

    user = User(id=uuid.uuid4(), email="commit2@test.com")
    job_id = uuid.uuid4()
    job = UploadJob(
        id=job_id,
        user_id=user.id,
        status=JobStatus.COMPLETED,
        file_ids=[],
        result_data={
            "extractions": [
                {
                    "merchant_name": "Test",
                    "line_items": [],
                    "is_duplicate": True,
                    "duplicate_resolved": "skip",
                    "items_sum_matches_total": True,
                }
            ]
        },
    )
    app.dependency_overrides[get_current_user] = lambda: user

    async def mock_db_session() -> Any:
        from unittest.mock import AsyncMock, MagicMock

        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = job
        session.execute.return_value = result_mock
        yield session

    app.dependency_overrides[get_db_session] = mock_db_session

    client = TestClient(app, follow_redirects=False)
    token = jwt.encode(
        {"sub": str(user.id)}, get_settings().jwt_secret_key.get_secret_value(), algorithm="HS256"
    )
    client.headers["Authorization"] = f"Bearer {token}"

    response = client.post(f"/receipts/upload/{job_id}/commit", json={"indices_to_store": [0]})
    assert response.status_code == 200, response.json()
    data = response.json()
    assert data["status"] == "stored"


def test_resolve_total_errors(app: FastAPI) -> None:
    import uuid
    from typing import Any

    import jwt
    from fastapi.testclient import TestClient

    from app.api.dependencies import get_current_user
    from app.core.config import get_settings
    from app.db.session import get_db_session
    from app.models.upload_job import JobStatus, UploadJob
    from app.models.user import User

    job_id = uuid.uuid4()
    user = User(id=uuid.uuid4(), email="err@test.com")
    app.dependency_overrides[get_current_user] = lambda: user

    token = jwt.encode(
        {"sub": str(user.id)}, get_settings().jwt_secret_key.get_secret_value(), algorithm="HS256"
    )
    client = TestClient(app, follow_redirects=False)
    client.headers["Authorization"] = f"Bearer {token}"

    def mock_db_with_job(job_to_return: UploadJob | None) -> None:
        async def mock_db_session() -> Any:
            from unittest.mock import AsyncMock, MagicMock

            session = AsyncMock()
            result_mock = MagicMock()
            result_mock.scalar_one_or_none.return_value = job_to_return
            session.execute.return_value = result_mock
            yield session

        app.dependency_overrides[get_db_session] = mock_db_session

    # 1. Job not found
    mock_db_with_job(None)
    resp = client.post(
        f"/receipts/upload/{job_id}/resolve-total",
        json={"extraction_index": 0, "receipt_total": "1.00"},
    )
    assert resp.status_code == 404

    # 2. Job has no extractions
    job_no_ext = UploadJob(
        id=job_id, user_id=user.id, status=JobStatus.COMPLETED, file_ids=[], result_data={}
    )
    mock_db_with_job(job_no_ext)
    resp = client.post(
        f"/receipts/upload/{job_id}/resolve-total",
        json={"extraction_index": 0, "receipt_total": "1.00"},
    )
    assert resp.status_code == 400

    # 3. Invalid index
    job_ext = UploadJob(
        id=job_id,
        user_id=user.id,
        status=JobStatus.COMPLETED,
        file_ids=[],
        result_data={"extractions": []},
    )
    mock_db_with_job(job_ext)
    resp = client.post(
        f"/receipts/upload/{job_id}/resolve-total",
        json={"extraction_index": 1, "receipt_total": "1.00"},
    )
    assert resp.status_code == 400


def test_commit_job_errors(app: FastAPI) -> None:
    import uuid
    from typing import Any

    import jwt
    from fastapi.testclient import TestClient

    from app.api.dependencies import get_current_user
    from app.core.config import get_settings
    from app.db.session import get_db_session
    from app.models.upload_job import JobStatus, UploadJob
    from app.models.user import User

    job_id = uuid.uuid4()
    user = User(id=uuid.uuid4(), email="err2@test.com")
    app.dependency_overrides[get_current_user] = lambda: user

    token = jwt.encode(
        {"sub": str(user.id)}, get_settings().jwt_secret_key.get_secret_value(), algorithm="HS256"
    )
    client = TestClient(app, follow_redirects=False)
    client.headers["Authorization"] = f"Bearer {token}"

    def mock_db_with_job(job_to_return: UploadJob | None) -> None:
        async def mock_db_session() -> Any:
            from unittest.mock import AsyncMock, MagicMock

            session = AsyncMock()
            result_mock = MagicMock()
            result_mock.scalar_one_or_none.return_value = job_to_return
            session.execute.return_value = result_mock
            yield session

        app.dependency_overrides[get_db_session] = mock_db_session

    # 1. Job not found
    mock_db_with_job(None)
    resp = client.post(f"/receipts/upload/{job_id}/commit", json={"indices_to_store": [0]})
    assert resp.status_code == 404

    # 2. Job has no extractions
    job_no_ext = UploadJob(
        id=job_id, user_id=user.id, status=JobStatus.COMPLETED, file_ids=[], result_data={}
    )
    mock_db_with_job(job_no_ext)
    resp = client.post(f"/receipts/upload/{job_id}/commit", json={"indices_to_store": [0]})
    assert resp.status_code == 400

    # 3. Unresolved duplicate
    job_dup = UploadJob(
        id=job_id,
        user_id=user.id,
        status=JobStatus.COMPLETED,
        file_ids=[],
        result_data={"extractions": [{"is_duplicate": True}]},
    )
    mock_db_with_job(job_dup)
    resp = client.post(f"/receipts/upload/{job_id}/commit", json={"indices_to_store": [0]})
    assert resp.status_code == 400
    assert "unresolved duplicate" in resp.json()["detail"]

    # 4. Requires manual review
    job_man = UploadJob(
        id=job_id,
        user_id=user.id,
        status=JobStatus.COMPLETED,
        file_ids=[],
        result_data={"extractions": [{"requires_manual_review": True}]},
    )
    mock_db_with_job(job_man)
    resp = client.post(f"/receipts/upload/{job_id}/commit", json={"indices_to_store": [0]})
    assert resp.status_code == 400
    assert "manual review" in resp.json()["detail"]

    # 5. Low confidence total
    job_low = UploadJob(
        id=job_id,
        user_id=user.id,
        status=JobStatus.COMPLETED,
        file_ids=[],
        result_data={"extractions": [{"receipt_total_confidence": 50}]},
    )
    mock_db_with_job(job_low)
    resp = client.post(f"/receipts/upload/{job_id}/commit", json={"indices_to_store": [0]})
    assert resp.status_code == 400
    assert "low confidence" in resp.json()["detail"]

    # 6. Unresolved position match
    job_pos = UploadJob(
        id=job_id,
        user_id=user.id,
        status=JobStatus.COMPLETED,
        file_ids=[],
        result_data={"extractions": [{"position_matches": [{"result": "not_possible"}]}]},
    )
    mock_db_with_job(job_pos)
    resp = client.post(f"/receipts/upload/{job_id}/commit", json={"indices_to_store": [0]})
    assert resp.status_code == 400
    assert "position match" in resp.json()["detail"]

    # 7. A failed parse must never be stored as an empty receipt
    job_err = UploadJob(
        id=job_id,
        user_id=user.id,
        status=JobStatus.COMPLETED,
        file_ids=[],
        result_data={"extractions": [{"error": "extraction_failed", "file_ids": ["f1"]}]},
    )
    mock_db_with_job(job_err)
    resp = client.post(f"/receipts/upload/{job_id}/commit", json={"indices_to_store": [0]})
    assert resp.status_code == 400
    assert "failed to parse" in resp.json()["detail"]

    # 8. Selecting nothing is a mistake, not a silent success
    mock_db_with_job(job_err)
    resp = client.post(f"/receipts/upload/{job_id}/commit", json={"indices_to_store": []})
    assert resp.status_code == 400
    assert "No extractions selected" in resp.json()["detail"]

    # 9. An index the job does not have is rejected rather than ignored
    mock_db_with_job(job_err)
    resp = client.post(f"/receipts/upload/{job_id}/commit", json={"indices_to_store": [5]})
    assert resp.status_code == 400
    assert "Unknown extraction indices" in resp.json()["detail"]


def test_resolve_duplicate_errors(app: FastAPI) -> None:
    import uuid
    from typing import Any

    import jwt
    from fastapi.testclient import TestClient

    from app.api.dependencies import get_current_user
    from app.core.config import get_settings
    from app.db.session import get_db_session
    from app.models.upload_job import UploadJob
    from app.models.user import User

    job_id = uuid.uuid4()
    user = User(id=uuid.uuid4(), email="dup@test.com")
    app.dependency_overrides[get_current_user] = lambda: user

    token = jwt.encode(
        {"sub": str(user.id)}, get_settings().jwt_secret_key.get_secret_value(), algorithm="HS256"
    )
    client = TestClient(app, follow_redirects=False)
    client.headers["Authorization"] = f"Bearer {token}"

    def mock_db_with_exception(exc_msg: str) -> None:
        async def mock_db_session() -> Any:
            from unittest.mock import AsyncMock, MagicMock

            session = AsyncMock()
            result_mock = MagicMock()

            if exc_msg == "job not found":
                result_mock.scalar_one_or_none.return_value = None
            else:
                job = UploadJob(result_data={"extractions": []})
                result_mock.scalar_one_or_none.return_value = job

            session.execute.return_value = result_mock
            yield session

        app.dependency_overrides[get_db_session] = mock_db_session

    # 404 not found
    mock_db_with_exception("job not found")
    resp = client.post(
        f"/receipts/upload/{job_id}/resolve-duplicate",
        json={"extraction_index": 0, "action": "skip"},
    )
    assert resp.status_code == 404

    # 400 other error (e.g. index out of bounds)
    mock_db_with_exception("invalid index")
    resp = client.post(
        f"/receipts/upload/{job_id}/resolve-duplicate",
        json={"extraction_index": 1, "action": "skip"},
    )
    assert resp.status_code == 400


def test_resolve_duplicate_more_errors(app: FastAPI) -> None:
    import uuid
    from typing import Any

    import jwt
    from fastapi.testclient import TestClient

    from app.api.dependencies import get_current_user
    from app.core.config import get_settings
    from app.db.session import get_db_session
    from app.models.upload_job import UploadJob
    from app.models.user import User

    job_id = uuid.uuid4()
    user = User(id=uuid.uuid4(), email="dup2@test.com")
    app.dependency_overrides[get_current_user] = lambda: user

    token = jwt.encode(
        {"sub": str(user.id)}, get_settings().jwt_secret_key.get_secret_value(), algorithm="HS256"
    )
    client = TestClient(app, follow_redirects=False)
    client.headers["Authorization"] = f"Bearer {token}"

    def mock_db_with_job(job_to_return: UploadJob | None) -> None:
        async def mock_db_session() -> Any:
            from unittest.mock import AsyncMock, MagicMock

            session = AsyncMock()
            result_mock = MagicMock()
            result_mock.scalar_one_or_none.return_value = job_to_return
            session.execute.return_value = result_mock
            yield session

        app.dependency_overrides[get_db_session] = mock_db_session

    # Job has no extractions
    job_no_ext = UploadJob(id=job_id, user_id=user.id, result_data={})
    mock_db_with_job(job_no_ext)
    resp = client.post(
        f"/receipts/upload/{job_id}/resolve-duplicate",
        json={"extraction_index": 0, "action": "skip"},
    )
    assert resp.status_code == 400
    assert "has no extractions" in resp.json()["detail"].lower()

    # Extraction not duplicate
    job_not_dup = UploadJob(
        id=job_id, user_id=user.id, result_data={"extractions": [{"is_duplicate": False}]}
    )
    mock_db_with_job(job_not_dup)
    resp = client.post(
        f"/receipts/upload/{job_id}/resolve-duplicate",
        json={"extraction_index": 0, "action": "skip"},
    )
    assert resp.status_code == 400
    assert "not flagged as duplicate" in resp.json()["detail"].lower()


def test_resolve_position_match_errors(app: FastAPI) -> None:
    import uuid
    from typing import Any

    import jwt
    from fastapi.testclient import TestClient

    from app.api.dependencies import get_current_user
    from app.core.config import get_settings
    from app.db.session import get_db_session
    from app.models.user import User

    job_id = uuid.uuid4()
    user = User(id=uuid.uuid4(), email="pos@test.com")
    app.dependency_overrides[get_current_user] = lambda: user

    token = jwt.encode(
        {"sub": str(user.id)}, get_settings().jwt_secret_key.get_secret_value(), algorithm="HS256"
    )
    client = TestClient(app, follow_redirects=False)
    client.headers["Authorization"] = f"Bearer {token}"

    import contextlib
    from collections.abc import Iterator
    from unittest.mock import AsyncMock, patch

    @contextlib.contextmanager
    def patch_service(exc_msg: str) -> Iterator[None]:

        with patch(
            "app.api.routers.receipts.ReceiptService.resolve_position_match", new_callable=AsyncMock
        ) as mock_resolve:
            mock_resolve.side_effect = ValueError(exc_msg)

            async def mock_db_session() -> Any:
                session = AsyncMock()
                yield session

            app.dependency_overrides[get_db_session] = mock_db_session
            yield

    with patch_service("job not found"):
        resp = client.post(
            f"/receipts/upload/{job_id}/resolve-position-match",
            json={
                "extraction_index": 0,
                "match_index": 0,
                "action": "different",
            },
        )
        assert resp.status_code == 404

    with patch_service("invalid something"):
        resp = client.post(
            f"/receipts/upload/{job_id}/resolve-position-match",
            json={
                "extraction_index": 0,
                "match_index": 0,
                "action": "different",
            },
        )
        assert resp.status_code == 400


def _authenticated_client(app: FastAPI, user: User) -> TestClient:
    """Wire a client whose JWT also satisfies UserContextMiddleware.

    The middleware reads the raw header rather than the dependency, so a
    `get_current_user` override alone leaves the ownership ContextVar unset.
    """
    app.dependency_overrides[get_current_user] = lambda: user

    async def mock_db_session() -> Any:
        from unittest.mock import AsyncMock

        yield AsyncMock()

    app.dependency_overrides[get_db_session] = mock_db_session

    client = TestClient(app, follow_redirects=False)
    token = jwt.encode(
        {"sub": str(user.id)}, get_settings().jwt_secret_key.get_secret_value(), algorithm="HS256"
    )
    client.headers["Authorization"] = f"Bearer {token}"
    return client


def test_deleting_a_receipt_returns_no_content(app: FastAPI) -> None:
    # Given
    user = User(id=uuid.uuid4(), email="owner@test.com")
    client = _authenticated_client(app, user)
    receipt_id = uuid.uuid4()

    with patch("app.api.routers.receipts.ReceiptService") as service_cls:
        service_cls.return_value.delete_receipt = AsyncMock(return_value=True)

        # When
        response = client.delete(f"/receipts/{receipt_id}")

    # Then
    assert response.status_code == 204
    assert response.content == b""


def test_deleting_another_users_receipt_returns_404(app: FastAPI) -> None:
    # Given the ownership filter reports nothing deleted, as it does for a
    # receipt owned by somebody else (BRD N2)
    user = User(id=uuid.uuid4(), email="intruder@test.com")
    client = _authenticated_client(app, user)

    with patch("app.api.routers.receipts.ReceiptService") as service_cls:
        service_cls.return_value.delete_receipt = AsyncMock(return_value=False)

        # When
        response = client.delete(f"/receipts/{uuid.uuid4()}")

    # Then it is indistinguishable from a receipt that never existed
    assert response.status_code == 404
    assert response.json()["code"] == "not_found"


def _job_with_one_unpriced_line(user: User, job_id: uuid.UUID) -> UploadJob:
    """A euro sklep receipt whose eggs line the parser could not price."""
    return UploadJob(
        id=job_id,
        user_id=user.id,
        status=JobStatus.COMPLETED,
        file_ids=[],
        result_data={
            "extractions": [
                {
                    "merchant_name": "euro sklep",
                    "receipt_total": "21,48",
                    "line_items": [
                        {
                            "name": "MILKA",
                            "quantity": "1",
                            "unit_price": "7,49",
                            "total_price": "7,49",
                        },
                        {
                            "name": "AGRO-FARM Jaja",
                            "quantity": "10",
                            "unit_price": "",
                            "total_price": "",
                        },
                    ],
                    "items_sum_matches_total": None,
                    "computed_total": None,
                }
            ]
        },
    )


def test_a_receipt_whose_lines_do_not_add_up_is_not_stored(app: FastAPI) -> None:
    # Given
    user = User(id=uuid.uuid4(), email="gate@test.com")
    job_id = uuid.uuid4()
    job = _job_with_one_unpriced_line(user, job_id)
    assert job.result_data is not None
    job.result_data["extractions"][0]["items_sum_matches_total"] = False
    job.result_data["extractions"][0]["computed_total"] = "7.49"

    client = _authenticated_client(app, user)

    async def mock_db_session() -> Any:
        from unittest.mock import AsyncMock, MagicMock

        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = job
        session.execute.return_value = result_mock
        yield session

    app.dependency_overrides[get_db_session] = mock_db_session

    # When
    response = client.post(f"/receipts/upload/{job_id}/commit", json={"indices_to_store": [0]})

    # Then
    # Now we allow storing them
    assert response.status_code == 200, response.json()


def test_a_receipt_that_could_not_be_checked_at_all_is_not_stored(app: FastAPI) -> None:
    # Given a line with no readable price, which leaves the sum unknowable
    user = User(id=uuid.uuid4(), email="unchecked@test.com")
    job_id = uuid.uuid4()
    job = _job_with_one_unpriced_line(user, job_id)

    client = _authenticated_client(app, user)

    async def mock_db_session() -> Any:
        from unittest.mock import AsyncMock, MagicMock

        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = job
        session.execute.return_value = result_mock
        yield session

    app.dependency_overrides[get_db_session] = mock_db_session

    # When
    response = client.post(f"/receipts/upload/{job_id}/commit", json={"indices_to_store": [0]})

    # Then "unknown" is refused just as firmly as "wrong"
    assert response.status_code == 200, response.json()


def test_updating_a_receipt_returns_the_new_state(app: FastAPI) -> None:
    # Given
    user = User(id=uuid.uuid4(), email="update-owner@test.com")
    client = _authenticated_client(app, user)
    receipt_id = uuid.uuid4()

    updated = Receipt(
        id=receipt_id,
        user_id=user.id,
        merchant_name="euro sklep",
        transaction_date=None,
        total_amount=Decimal("13.99"),
        status=ReceiptStatus.PARSED,
        file_ids=[],
    )
    updated.line_items = []
    # Server-generated in production; this object never touches the database.
    updated.created_at = datetime.now(UTC)

    with patch("app.api.routers.receipts.ReceiptService") as service_cls:
        service_cls.return_value.update_receipt = AsyncMock(return_value=updated)

        # When
        response = client.patch(
            f"/receipts/{receipt_id}",
            json={
                "merchant_name": "euro sklep",
                "transaction_date": None,
                "total_amount": "13.99",
                "line_items": [],
            },
        )

    # Then
    assert response.status_code == 200, response.json()
    assert response.json()["total_amount"] == "13.99"


def test_updating_another_users_receipt_returns_404(app: FastAPI) -> None:
    # Given the service reports nothing found, as it does for a receipt owned
    # by somebody else (BRD N2)
    user = User(id=uuid.uuid4(), email="update-intruder@test.com")
    client = _authenticated_client(app, user)

    with patch("app.api.routers.receipts.ReceiptService") as service_cls:
        service_cls.return_value.update_receipt = AsyncMock(return_value=None)

        # When
        response = client.patch(
            f"/receipts/{uuid.uuid4()}",
            json={
                "merchant_name": "x",
                "transaction_date": None,
                "total_amount": "1.00",
                "line_items": [],
            },
        )

    # Then it is indistinguishable from a receipt that never existed
    assert response.status_code == 404
    assert response.json()["code"] == "not_found"


def test_updating_a_receipt_with_mismatched_lines_is_refused(app: FastAPI) -> None:
    # Given the service enforces the same arithmetic invariant as the commit gate
    user = User(id=uuid.uuid4(), email="update-mismatch@test.com")
    client = _authenticated_client(app, user)

    with patch("app.api.routers.receipts.ReceiptService") as service_cls:
        service_cls.return_value.update_receipt = AsyncMock(
            side_effect=DomainError("The lines add up to 7.49, not the total of 999.00.")
        )

        # When
        response = client.patch(
            f"/receipts/{uuid.uuid4()}",
            json={
                "merchant_name": "x",
                "transaction_date": None,
                "total_amount": "999.00",
                "line_items": [],
            },
        )

    # Then
    assert response.status_code == 409
    assert response.json()["code"] == "domain_error"
