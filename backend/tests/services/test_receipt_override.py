import uuid
from unittest.mock import AsyncMock

import pytest

from app.models.upload_job import JobStatus, UploadJob
from app.schemas.receipt import ResolvePositionMatchRequest
from app.services.receipt import ReceiptService


@pytest.mark.asyncio
async def test_service_resolve_position_match() -> None:
    user_id = uuid.uuid4()
    job_id = uuid.uuid4()

    mock_job = UploadJob(id=job_id, user_id=user_id, status=JobStatus.COMPLETED, file_ids=[])
    mock_job.result_data = {
        "extractions": [
            {
                "merchant_name": "Test",
                "line_items": [
                    {"name": "Apple", "quantity": "1", "unit_price": "1.0", "total_price": "1.0"},
                    {"name": "Apple", "quantity": "1", "unit_price": "1.0", "total_price": "1.0"},
                ],
                "position_matches": [{"item_a_index": 0, "item_b_index": 1, "result": "same"}],
            }
        ]
    }

    mock_repo = AsyncMock()
    mock_repo.get_upload_job.return_value = mock_job

    service = ReceiptService(repository=mock_repo)
    req = ResolvePositionMatchRequest(extraction_index=0, match_index=0, action="different")

    res = await service.resolve_position_match(job_id, user_id, req)

    assert res.job_id == job_id
    assert res.extracted_data is not None
    assert res.extracted_data["extractions"][0]["position_matches"][0]["result"] == "different"
    assert res.extracted_data["extractions"][0]["position_matches"][0]["user_overridden"] is True

    # Also check arithmetic re-validation occurred
    # (computed_total should be 2.0 because "different" means two distinct items)
    assert res.extracted_data["extractions"][0]["computed_total"] == "2.0"

    mock_repo.add_position_match_override.assert_called_once()
    override_arg = mock_repo.add_position_match_override.call_args[0][0]
    assert override_arg.original_result == "same"
    assert override_arg.corrected_result == "different"
    assert override_arg.user_id == user_id
