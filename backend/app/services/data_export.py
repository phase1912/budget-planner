"""Everything held about a user, in one archive (F17.9.2, GDPR art. 15 and 20)."""

import asyncio
import io
import json
import logging
import uuid
import zipfile
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any

import filetype  # type: ignore[import-untyped]
from sqlalchemy import Table, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import Model
from app.models.household import Household
from app.models.line_item import LineItem
from app.models.receipt import Receipt
from app.models.user import User
from app.ports.storage import StoragePort, receipt_object_name

logger = logging.getLogger(__name__)

WITHHELD_TABLES = frozenset({"refresh_tokens"})
"""Session secrets: handing them out would hand out the account, and they are no one's data."""
WITHHELD_COLUMNS = frozenset({"password_hash", "two_factor_secret", "recovery_code_hashes"})
"""Credentials, not information about the person: the password's hash, the authenticator
secret and the recovery codes' hashes (F18.6.1) — an archive must never open the account."""


def _plain(value: Any) -> Any:
    """A column value as JSON writes it: ids, money and moments as text."""
    if isinstance(value, uuid.UUID | Decimal):
        return str(value)
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    return value


def _row(mapping: Any) -> dict[str, Any]:
    return {key: _plain(value) for key, value in mapping.items() if key not in WITHHELD_COLUMNS}


def owned_tables() -> list[Table]:
    """Every table that holds rows of one user's, by its `user_id` column.

    Found from the models rather than listed, so a table added later is in the archive
    without anyone remembering to add it.
    """
    return [
        table
        for table in Model.metadata.sorted_tables
        if "user_id" in table.c and table.name not in WITHHELD_TABLES
    ]


async def account_data(session: AsyncSession, user_id: uuid.UUID) -> dict[str, Any]:
    """The user's account and every row of theirs, by table, receipts' lines included."""
    account = (
        await session.execute(select(User.__table__).where(User.id == user_id))
    ).one_or_none()
    if account is None:
        raise ValueError("The export's owner is gone")
    tables: dict[str, list[dict[str, Any]]] = {}
    for table in owned_tables():
        rows = await session.execute(select(table).where(table.c.user_id == user_id))
        tables[table.name] = [_row(row._mapping) for row in rows]
    lines = await session.execute(
        select(LineItem.__table__)
        .join(Receipt, Receipt.id == LineItem.receipt_id)
        .where(Receipt.user_id == user_id)
    )
    tables["line_items"] = [_row(row._mapping) for row in lines]
    # The household the user is in, by name; its other members' data is theirs, not here.
    joined = [m["household_id"] for m in tables.get("household_members", [])]
    households = await session.execute(
        select(Household.__table__).where(Household.id.in_([uuid.UUID(h) for h in joined]))
    )
    tables["households"] = [_row(row._mapping) for row in households]
    return {
        "exported_at": datetime.now(UTC).isoformat(),
        "account": _row(account._mapping),
        "tables": tables,
    }


async def account_archive(session: AsyncSession, storage: StoragePort, user_id: uuid.UUID) -> bytes:
    """A ZIP of `data.json` and `photos/`: every receipt photo still kept (F17.9.3).

    A photo storage no longer has — removed after 90 days — is simply not in it; the
    receipt it belonged to is in the data, with its lines and totals.
    """
    data = await account_data(session, user_id)
    photos: dict[str, bytes] = {}
    for receipt in data["tables"].get("receipts", []):
        for file_id in receipt.get("file_ids") or []:
            try:
                photos[file_id] = await storage.download_file(receipt_object_name(user_id, file_id))
            except Exception:
                logger.info("Photo %s of an exported receipt is no longer kept", file_id)
    return await asyncio.to_thread(_zip, data, photos)


def _zip(data: dict[str, Any], photos: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("data.json", json.dumps(data, ensure_ascii=False, indent=2))
        for file_id, content in photos.items():
            kind = filetype.guess(content)
            extension = f".{kind.extension}" if kind else ""
            # Photos are already compressed; deflating them again only costs time.
            archive.writestr(f"photos/{file_id}{extension}", content, zipfile.ZIP_STORED)
    return buffer.getvalue()
