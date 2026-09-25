#!/usr/bin/env python
"""Seed a demo user with real, categorised receipts (F5.8).

`load` (the default) recreates `demo@budget-agent.local` from the fixture in
`scripts/seed_data/demo_receipts.json`, so the monthly-budget and statistics
epics (E6, E7) can be exercised without photographing or parsing anything.
`export` writes that fixture from a real account's stored receipts, which is
how it was made: the data is genuine uploads, not invented numbers.

Only receipt data travels: merchant, date, total, status, lines and their
categories. Photos, users and anything else stay behind.

Usage:
    uv run python scripts/seed_demo_data.py                  # load
    uv run python scripts/seed_demo_data.py export --email you@example.com
"""

import argparse
import asyncio
import calendar
import json
import sys
from collections.abc import Sequence
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import get_password_hash
from app.domain.categories import UNCATEGORIZED
from app.models.category import Category
from app.models.line_item import LineItem
from app.models.receipt import Receipt, ReceiptStatus
from app.models.upload_job import UploadJob
from app.models.user import User

FIXTURE = Path(__file__).resolve().parent / "seed_data" / "demo_receipts.json"
DEMO_EMAIL = "demo@budget-agent.local"
DEMO_PASSWORD = "demo-budget-agent"
"""Local development only: the account exists solely where someone ran `make seed`."""

DEMO_BUDGET_LIMIT = Decimal("3000.00")


def shift_months(moment: datetime, months: int) -> datetime:
    """Move a timestamp by whole calendar months, keeping the day where it exists.

    A 31st moved into a 30-day month lands on the 30th, never in the month after.
    """
    month_index = moment.year * 12 + moment.month - 1 + months
    year, month = divmod(month_index, 12)
    last_day = calendar.monthrange(year, month + 1)[1]
    return moment.replace(year=year, month=month + 1, day=min(moment.day, last_day))


def months_until(latest: datetime, today: date) -> int:
    """How many whole months bring `latest` into the month of `today`.

    Applied to every receipt alike, so the newest lands in the current month and
    the rest keep their spacing: "this month" and "last month" always have data.
    """
    return (today.year - latest.year) * 12 + (today.month - latest.month)


async def export_receipts(session: AsyncSession, email: str) -> dict[str, Any]:
    """The fixture: one account's stored receipts and the custom categories they use."""
    user = (await session.execute(select(User).where(User.email == email))).scalar_one()
    receipts = (
        (
            await session.execute(
                select(Receipt)
                .where(Receipt.user_id == user.id, Receipt.transaction_date.is_not(None))
                .options(selectinload(Receipt.line_items).selectinload(LineItem.category))
                .order_by(Receipt.transaction_date)
            )
        )
        .scalars()
        .all()
    )
    custom = sorted(
        {
            item.category.name
            for receipt in receipts
            for item in receipt.line_items
            if item.category is not None and item.category.user_id is not None
        }
    )
    return {
        "custom_categories": custom,
        "receipts": [
            {
                "merchant_name": receipt.merchant_name,
                "transaction_date": receipt.transaction_date.isoformat()
                if receipt.transaction_date
                else None,
                "total_amount": str(receipt.total_amount)
                if receipt.total_amount is not None
                else None,
                "status": receipt.status.value,
                "line_items": [
                    {
                        "name": item.name,
                        "quantity": str(item.quantity),
                        "unit_price": str(item.unit_price),
                        "total_price": str(item.total_price),
                        "category": item.category.name if item.category else UNCATEGORIZED,
                        "category_confidence": item.category_confidence,
                        "is_category_manual": item.is_category_manual,
                    }
                    for item in receipt.line_items
                ],
            }
            for receipt in receipts
        ],
    }


async def load_demo(session: AsyncSession, fixture: dict[str, Any], today: date) -> User:
    """Recreate the demo user from a fixture, dated so its newest month is `today`'s.

    Idempotent: an existing demo user is deleted first, with everything it owns,
    so running it twice gives the same account rather than two copies. Does not
    commit; the caller decides, which is what lets tests roll it back.
    """
    existing = select(User.id).where(User.email == DEMO_EMAIL)
    # Upload jobs are the one table without ON DELETE CASCADE to users.
    await session.execute(delete(UploadJob).where(UploadJob.user_id.in_(existing)))
    await session.execute(delete(User).where(User.email == DEMO_EMAIL))

    user = User(
        email=DEMO_EMAIL,
        first_name="Demo",
        last_name="User",
        password_hash=get_password_hash(DEMO_PASSWORD),
        currency="PLN",
        budget_limit=DEMO_BUDGET_LIMIT,
    )
    session.add(user)
    await session.flush()

    categories = await _categories_for(session, user, fixture.get("custom_categories", []))
    dated = [
        (datetime.fromisoformat(r["transaction_date"]), r)
        for r in fixture["receipts"]
        if r.get("transaction_date")
    ]
    offset = months_until(max(moment for moment, _ in dated), today) if dated else 0

    for moment, data in dated:
        receipt = Receipt(
            user_id=user.id,
            merchant_name=data.get("merchant_name"),
            transaction_date=shift_months(moment.astimezone(UTC), offset),
            total_amount=Decimal(data["total_amount"]) if data.get("total_amount") else None,
            status=ReceiptStatus(data.get("status", ReceiptStatus.PARSED.value)),
            file_ids=[],
        )
        session.add(receipt)
        await session.flush()
        await session.refresh(receipt, ["line_items"])
        receipt.line_items = [
            LineItem(
                name=item["name"],
                quantity=Decimal(item["quantity"]),
                unit_price=Decimal(item["unit_price"]),
                total_price=Decimal(item["total_price"]),
                category=categories.get(item.get("category") or "", categories[UNCATEGORIZED]),
                category_confidence=item.get("category_confidence"),
                is_category_manual=bool(item.get("is_category_manual", False)),
            )
            for item in data["line_items"]
        ]
    await session.flush()
    return user


async def _categories_for(
    session: AsyncSession, user: User, custom_names: Sequence[str]
) -> dict[str, Category]:
    """The categories the demo user can file under, by name: built-ins plus its own."""
    for name in custom_names:
        session.add(Category(user_id=user.id, name=name))
    await session.flush()
    visible = await session.execute(
        select(Category).where(or_(Category.user_id.is_(None), Category.user_id == user.id))
    )
    return {category.name: category for category in visible.scalars()}


async def _main(argv: Sequence[str]) -> None:
    from app.db.session import get_session_factory

    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0] if __doc__ else None)
    commands = parser.add_subparsers(dest="command")
    export = commands.add_parser("export", help="write the fixture from an account's receipts")
    export.add_argument("--email", required=True)
    commands.add_parser("load", help="recreate the demo user from the fixture (default)")
    args = parser.parse_args(argv)

    async with get_session_factory()() as session:
        if args.command == "export":
            fixture = await export_receipts(session, args.email)
            FIXTURE.parent.mkdir(parents=True, exist_ok=True)
            FIXTURE.write_text(json.dumps(fixture, indent=2, ensure_ascii=False) + "\n")
            print(f"Exported {len(fixture['receipts'])} receipts to {FIXTURE}")
            return

        fixture = json.loads(FIXTURE.read_text())
        user = await load_demo(session, fixture, datetime.now(UTC).date())
        await session.commit()
        print(
            f"Seeded {len(fixture['receipts'])} receipts for {user.email} "
            f"(password: {DEMO_PASSWORD})"
        )


if __name__ == "__main__":
    asyncio.run(_main(sys.argv[1:]))
