"""A receipt the user already has is recognised, by fiscal identity or by likeness (F11.5).

Exact copies — the same fiscal register and receipt number — are never stored twice,
whichever channel brought them; receipts that only look alike are put to the user
(BRD A14, ADR-0015).
"""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.receipt import Receipt
from app.models.user import User
from app.repository.receipt import ReceiptRepository
from app.schemas.extraction import ExtractedReceipt
from app.services.receipt import _mark_duplicates
from tests.api.test_inbound_email import (  # noqa: F401 — relay_settings is a fixture
    StubParser,
    _address,
    _deliver,
    _message,
    relay_settings,
)
from tests.api.test_upload_wizard_persistence import _job, _post
from tests.factories.receipt import ReceiptFactory
from tests.factories.user import UserFactory

REGISTER, NUMBER = "ECA2201079960", "85503"


def _reading(**overrides: Any) -> dict[str, Any]:
    return {
        "merchant_name": "Rossmann",
        "transaction_date": "2026-09-14",
        "receipt_total": "12.50",
        "requires_manual_review": False,
        "line_items": [
            {"name": "Krem", "quantity": "1", "unit_price": "12.50", "total_price": "12.50"},
        ],
        **overrides,
    }


async def _stored_rossmann(user: User, **fiscal: Any) -> Receipt:
    return await ReceiptFactory.create_async(
        user_id=user.id,
        merchant_name="Rossmann",
        transaction_date=datetime(2026, 9, 14, tzinfo=UTC),
        total_amount=Decimal("12.50"),
        file_ids=[],
        **fiscal,
    )


async def _receipts(session: AsyncSession, user: User) -> list[Receipt]:
    rows = await session.execute(select(Receipt).where(Receipt.user_id == user.id))
    return list(rows.scalars())


async def _commit(session: AsyncSession, user: User, extractions: list[dict[str, Any]]) -> None:
    job = await _job(user, extractions[0])
    job.result_data = {"extractions": extractions}
    response = await _post(
        session,
        user,
        f"/receipts/upload/{job.id}/commit",
        {"indices_to_store": list(range(len(extractions)))},
    )
    assert response.status_code == 200, response.json()


# --- the wizard -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_a_photo_of_a_receipt_already_stored_is_reported_with_when_it_was_added(
    db_session: AsyncSession,
) -> None:
    user = await UserFactory.create_async()
    stored = await _stored_rossmann(user, fiscal_register_id=REGISTER, fiscal_receipt_number=NUMBER)
    reading = _reading(fiscal_register_id="ECA 2201079960", fiscal_receipt_number="nr:85503")

    await _mark_duplicates(ReceiptRepository(db_session).bypass_ownership(), user.id, reading)

    assert reading["already_stored"]["receipt_id"] == str(stored.id)
    assert reading["already_stored"]["created_at"] == stored.created_at.isoformat()
    assert reading["is_duplicate"] is False


@pytest.mark.asyncio
async def test_alike_receipts_with_different_fiscal_numbers_are_two_purchases(
    db_session: AsyncSession,
) -> None:
    """Two visits to one shop on one day for the same amount are not a duplicate."""
    user = await UserFactory.create_async()
    await _stored_rossmann(user, fiscal_register_id=REGISTER, fiscal_receipt_number=NUMBER)
    reading = _reading(fiscal_register_id=REGISTER, fiscal_receipt_number="85504")

    await _mark_duplicates(ReceiptRepository(db_session).bypass_ownership(), user.id, reading)

    assert "already_stored" not in reading
    assert reading["is_duplicate"] is False


@pytest.mark.asyncio
async def test_without_fiscal_numbers_a_lookalike_is_put_to_the_user(
    db_session: AsyncSession,
) -> None:
    user = await UserFactory.create_async()
    await _stored_rossmann(user, fiscal_register_id=REGISTER, fiscal_receipt_number=NUMBER)
    reading = _reading()

    await _mark_duplicates(ReceiptRepository(db_session).bypass_ownership(), user.id, reading)

    assert reading["is_duplicate"] is True


@pytest.mark.asyncio
async def test_another_users_receipt_is_never_reported_as_already_stored(
    db_session: AsyncSession,
) -> None:
    """BRD N2: one user's fiscal numbers say nothing about another user's receipts."""
    owner, other = await UserFactory.create_async(), await UserFactory.create_async()
    await _stored_rossmann(other, fiscal_register_id=REGISTER, fiscal_receipt_number=NUMBER)
    reading = _reading(fiscal_register_id=REGISTER, fiscal_receipt_number=NUMBER)

    await _mark_duplicates(ReceiptRepository(db_session).bypass_ownership(), owner.id, reading)

    assert "already_stored" not in reading
    assert reading["is_duplicate"] is False


@pytest.mark.asyncio
async def test_a_duplicate_the_user_skipped_is_not_stored(db_session: AsyncSession) -> None:
    user = await UserFactory.create_async()

    await _commit(
        db_session,
        user,
        [
            _reading(duplicate_resolved="skipped", is_skipped=True, receipt_total=None),
            _reading(merchant_name="Biedronka"),
        ],
    )

    assert [r.merchant_name for r in await _receipts(db_session, user)] == ["Biedronka"]


@pytest.mark.asyncio
async def test_a_receipt_already_stored_is_left_out_of_the_commit(
    db_session: AsyncSession,
) -> None:
    user = await UserFactory.create_async()
    await _stored_rossmann(user, fiscal_register_id=REGISTER, fiscal_receipt_number=NUMBER)

    await _commit(
        db_session,
        user,
        [
            _reading(already_stored={"receipt_id": "x"}),
            _reading(merchant_name="Biedronka"),
        ],
    )

    assert sorted(r.merchant_name or "" for r in await _receipts(db_session, user)) == [
        "Biedronka",
        "Rossmann",
    ]


@pytest.mark.asyncio
async def test_two_photos_of_one_receipt_in_one_upload_are_stored_once(
    db_session: AsyncSession,
) -> None:
    user = await UserFactory.create_async()
    shot = _reading(fiscal_register_id=REGISTER, fiscal_receipt_number=NUMBER)

    await _commit(db_session, user, [shot, dict(shot)])

    [receipt] = await _receipts(db_session, user)
    assert (receipt.fiscal_register_id, receipt.fiscal_receipt_number) == (REGISTER, NUMBER)


# --- email ------------------------------------------------------------------------


class FiscalParser(StubParser):
    """The stub e-receipt, carrying fiscal numbers when given them."""

    def __init__(self, register: str | None = None, number: str | None = None) -> None:
        super().__init__()
        self.fiscal = {"fiscal_register_id": register, "fiscal_receipt_number": number}

    async def parse(
        self, images: list[bytes], *, mime_types: list[str] | None = None
    ) -> ExtractedReceipt:
        reading = await super().parse(images, mime_types=mime_types)
        return reading.model_copy(update=self.fiscal)


async def _forward(session: AsyncSession, user: User, parser: StubParser, msg_id: str) -> None:
    raw = _message(user.email, html="<p>receipt</p>", msg_id=msg_id)
    await _deliver(session, _address(user), raw, parser=parser)


@pytest.mark.asyncio
@pytest.mark.usefixtures("relay_settings")
async def test_an_emailed_receipt_already_stored_is_not_stored_again(
    db_session: AsyncSession,
) -> None:
    user = await UserFactory.create_async(email="shopper@example.com")
    parser = FiscalParser(REGISTER, NUMBER)

    await _forward(db_session, user, parser, "<first@shop>")
    await _forward(db_session, user, parser, "<second@shop>")

    assert len(await _receipts(db_session, user)) == 1


@pytest.mark.asyncio
@pytest.mark.usefixtures("relay_settings")
async def test_an_emailed_lookalike_is_stored_and_marked(db_session: AsyncSession) -> None:
    user = await UserFactory.create_async(email="shopper@example.com")

    await _forward(db_session, user, StubParser(), "<first@shop>")
    await _forward(db_session, user, StubParser(), "<second@shop>")

    first, second = sorted(
        await _receipts(db_session, user), key=lambda r: r.source_reference or ""
    )
    assert first.possible_duplicate_of_id is None
    assert second.possible_duplicate_of_id == first.id


@pytest.mark.asyncio
async def test_keeping_both_clears_the_mark(db_session: AsyncSession) -> None:
    user = await UserFactory.create_async()
    original = await _stored_rossmann(user)
    copy = await _stored_rossmann(user, possible_duplicate_of_id=original.id)

    response = await _post(db_session, user, f"/receipts/{copy.id}/keep-duplicate", None)

    assert response.status_code == 200, response.json()
    assert response.json()["possible_duplicate_of_id"] is None
    await db_session.refresh(copy)
    assert copy.possible_duplicate_of_id is None


@pytest.mark.asyncio
async def test_another_users_mark_cannot_be_cleared(db_session: AsyncSession) -> None:
    """BRD N2."""
    owner, other = await UserFactory.create_async(), await UserFactory.create_async()
    original = await _stored_rossmann(owner)
    copy = await _stored_rossmann(owner, possible_duplicate_of_id=original.id)

    response = await _post(db_session, other, f"/receipts/{copy.id}/keep-duplicate", None)

    assert response.status_code == 404
    await db_session.refresh(copy)
    assert copy.possible_duplicate_of_id == original.id
