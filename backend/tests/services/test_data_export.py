"""Everything held about a user, in one archive (F17.9.2, BRD N2)."""

import io
import json
import zipfile
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.household import HouseholdRole
from app.models.line_item import LineItem
from app.models.refresh_token import RefreshToken
from app.ports.storage import receipt_object_name
from app.services.data_export import account_archive
from app.services.storage import ObjectNotFoundError
from tests.factories.goal import GoalFactory
from tests.factories.household import HouseholdFactory, HouseholdMemberFactory
from tests.factories.receipt import ReceiptFactory
from tests.factories.user import UserFactory

JPEG = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00" + b"\x00" * 64


class Photos:
    """Storage holding some photos; any other name is gone."""

    def __init__(self, files: dict[str, bytes]) -> None:
        self.files = files

    async def download_file(self, object_name: str) -> bytes:
        if object_name not in self.files:
            raise ObjectNotFoundError(object_name)
        return self.files[object_name]


@pytest.mark.asyncio
async def test_the_archive_holds_the_users_data_and_kept_photos_and_no_one_elses(
    db_session: AsyncSession,
) -> None:
    user = await UserFactory.create_async(first_name="Ann", password_hash="secret-hash")
    stranger = await UserFactory.create_async()
    receipt = await ReceiptFactory.create_async(
        user_id=user.id, merchant_name="Lidl", file_ids=["kept", "expired"]
    )
    db_session.add(
        LineItem(
            receipt_id=receipt.id,
            name="Milk",
            quantity=Decimal(1),
            unit_price=Decimal("3.49"),
            total_price=Decimal("3.49"),
        )
    )
    await GoalFactory.create_async(user_id=user.id)
    await ReceiptFactory.create_async(user_id=stranger.id, merchant_name="Not hers")
    household = await HouseholdFactory.create_async(name="Our flat")
    await HouseholdMemberFactory.create_async(
        household_id=household.id, user_id=user.id, role=HouseholdRole.OWNER.value
    )
    db_session.add(
        RefreshToken(
            user_id=user.id,
            token="session-secret",
            family_id=user.id,
            expires_at=datetime.now(UTC) + timedelta(days=1),
        )
    )
    await db_session.flush()
    storage = Photos({receipt_object_name(user.id, "kept"): JPEG})

    content = await account_archive(db_session, storage, user.id)  # type: ignore[arg-type]

    archive = zipfile.ZipFile(io.BytesIO(content))
    assert archive.namelist() == ["data.json", "photos/kept.jpg"]
    raw = archive.read("data.json").decode()
    data = json.loads(raw)
    tables = data["tables"]
    assert data["account"]["first_name"] == "Ann"
    assert [r["merchant_name"] for r in tables["receipts"]] == ["Lidl"]
    assert [line["name"] for line in tables["line_items"]] == ["Milk"]
    assert len(tables["goals"]) == 1
    assert [h["name"] for h in tables["households"]] == ["Our flat"]
    assert "refresh_tokens" not in tables
    assert "secret-hash" not in raw and "session-secret" not in raw and "Not hers" not in raw
