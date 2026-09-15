import uuid
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.api.dependencies import get_current_user
from app.main import create_app
from app.models.upload_job import JobStatus
from app.models.user import User
from app.schemas.receipt import UploadJobStatusResponse


def test_resolve_position_match() -> None:
    app = create_app()
    user = User(id=uuid.uuid4(), email="test@test.com")
    app.dependency_overrides[get_current_user] = lambda: user

    job_id = uuid.uuid4()

    mock_response = UploadJobStatusResponse(
        job_id=job_id, status=JobStatus.COMPLETED, file_ids=[], extracted_data={"extractions": []}
    )

    with patch(
        "app.api.routers.receipts.ReceiptService.resolve_position_match", new_callable=AsyncMock
    ) as mock_method:
        mock_method.return_value = mock_response

        from app.db.session import get_db_session

        class MockSession:
            async def commit(self) -> None:
                pass

        app.dependency_overrides[get_db_session] = lambda: MockSession()

        client = TestClient(app)
        res = client.post(
            f"/receipts/upload/{job_id}/resolve-position-match",
            headers={"Authorization": "Bearer fake"},
            json={"extraction_index": 0, "match_index": 0, "action": "different"},
        )

        assert res.status_code == 200
        assert res.json()["job_id"] == str(job_id)
        mock_method.assert_called_once()
