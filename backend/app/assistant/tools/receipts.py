"""A receipt found, reviewed, corrected or deleted by chat, and put on a trip (F21.6)."""

import json
import uuid
from datetime import date
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.api.errors import NotFoundError
from app.assistant.tools.base import (
    Amount,
    Answer,
    FormField,
    Reader,
    ToolContext,
    Writer,
    as_id,
    find_by_name,
)
from app.domain.categories import UNCATEGORIZED
from app.domain.receipt_totals import lines_match_total
from app.domain.trips import TripKind
from app.models.line_item import LineItem
from app.models.receipt import Receipt, ReceiptStatus
from app.repository.receipt import ReceiptRepository
from app.schemas.receipt import LineItemInput, UpdateReceiptRequest
from app.services.receipt import ReceiptService
from app.services.trip import TripDetails, TripService

REVIEW_LISTED = 10
"""How many receipts waiting for review one answer names."""


class ReceiptRef(BaseModel):
    """One of the user's receipts, by the id the receipts tool gave it."""

    receipt_id: str = Field(description="The `id` the receipts tool gave the receipt")


def _receipt_id(said: str) -> uuid.UUID | None:
    try:
        return uuid.UUID(said.strip())
    except ValueError:
        return None


async def own_receipt(ctx: ToolContext, said: str) -> Receipt | None:
    """The user's own receipt with its lines; another member's is not theirs to change (N2)."""
    receipt_id = _receipt_id(said)
    if receipt_id is None:
        return None
    return await ReceiptRepository(ctx.session).get_with_items(receipt_id)


def receipt_label(receipt: Receipt) -> str:
    """A receipt as a card names it: shop, day and total."""
    day = receipt.transaction_date.date().isoformat() if receipt.transaction_date else ""
    total = str(receipt.total_amount) if receipt.total_amount is not None else ""
    return " · ".join(p for p in (receipt.merchant_name or "", day, total) if p)


def lines_named(receipt: Receipt, said: str) -> list[LineItem]:
    """The receipt's lines the user meant: the same name, else those containing it."""
    wanted = said.strip().lower()
    exact = [i for i in receipt.line_items if i.name.lower() == wanted]
    return exact or [i for i in receipt.line_items if wanted in i.name.lower()]


def _lines_sum(receipt: Receipt) -> Decimal:
    return sum((i.total_price for i in receipt.line_items), Decimal(0))


def review_reasons(receipt: Receipt) -> list[str]:
    """Why a receipt is held out of the month, in the words the screens use (F15, D3)."""
    reasons = []
    if receipt.status == ReceiptStatus.FAILED:
        reasons.append("it could not be read")
    if receipt.possible_duplicate_of_id is not None:
        reasons.append("it may be a duplicate of another receipt")
    if receipt.status == ReceiptStatus.MANUAL_REVIEW:
        if receipt.original_currency and receipt.exchange_rate is None:
            reasons.append(f"no exchange rate for {receipt.original_currency} yet")
        elif receipt.total_amount is not None and not lines_match_total(
            _lines_sum(receipt), receipt.total_amount
        ):
            reasons.append(
                f"its lines add up to {_lines_sum(receipt)}, not the total {receipt.total_amount}"
            )
        elif not reasons:
            reasons.append("it waits for the user to check it")
    return reasons


class ReceiptLines(Reader):
    """One receipt with its status, why it waits for review, and its lines with
    their categories (C3, F15)."""

    name = "receipt_lines"
    description = (
        "One of the user's receipts: its status, why it waits for review if it does, "
        "and its lines with their prices and categories."
    )
    args = ReceiptRef

    async def read(self, ctx: ToolContext, args: ReceiptRef) -> Answer:
        receipt = await own_receipt(ctx, args.receipt_id)
        if receipt is None:
            return Answer(json.dumps({"error": "no receipt of the user's with that id"}))
        figures = {
            "id": str(receipt.id),
            "shop": receipt.merchant_name,
            "date": receipt.transaction_date.date().isoformat()
            if receipt.transaction_date
            else None,
            "total": str(receipt.total_amount) if receipt.total_amount is not None else None,
            "currency": ctx.user.currency,
            "status": receipt.status.value,
            "waits_because": review_reasons(receipt),
            "lines": [
                {
                    "name": line.name,
                    "quantity": str(line.quantity),
                    "total": str(line.total_price),
                    "category": line.category.name if line.category else UNCATEGORIZED,
                }
                for line in sorted(receipt.line_items, key=lambda i: i.position)
            ],
        }
        card = {"screen": "receipts", "to": f"/receipts?receipt={receipt.id}"}
        return Answer(json.dumps(figures), card)


class NoArgs(BaseModel):
    """Nothing to say: the tool reads the whole list."""


class ReceiptsToReview(Reader):
    """The receipts held out of the month, each with why (F15, D3)."""

    name = "receipts_to_review"
    description = (
        "Only for what waits for review: the user's receipts held out of the month, each with "
        "why. To find a receipt to look at or correct, use the receipts tool."
    )
    args = NoArgs

    async def read(self, ctx: ToolContext, args: NoArgs) -> Answer:
        repository = ReceiptRepository(ctx.session)
        found, count = await repository.list_paginated(
            skip=0, limit=REVIEW_LISTED, status=ReceiptStatus.MANUAL_REVIEW
        )
        receipts = []
        for r in found:
            full = await repository.get_with_items(r.id)
            if full is not None:
                receipts.append(
                    {"id": str(full.id), "receipt": receipt_label(full)}
                    | {"waits_because": review_reasons(full)}
                )
        card = {"screen": "receipts", "to": "/receipts?status=manual_review"}
        return Answer(json.dumps({"waiting": count, "receipts": receipts}), card)


class LineArgs(BaseModel):
    """A line of a receipt to correct, or a new line to add."""

    receipt_id: str = Field(description="The `id` the receipts tool gave the receipt")
    line: str | None = Field(
        None, max_length=120, description="The line to change, by its name; leave out to add one"
    )
    name: str | None = Field(None, max_length=255, description="The line's new name")
    quantity: Decimal | None = Field(None, gt=0, description="How many")
    total: Amount | None = Field(None, description="What the whole line cost")


class LineCard(BaseModel):
    """A line as the user approves it; `line_id` is empty for a new one."""

    target: str
    receipt_id: uuid.UUID
    line_id: uuid.UUID | None = None
    name: str = Field(min_length=1, max_length=255)
    quantity: Decimal = Field(gt=0)
    amount: Amount


def _input(line: LineItem) -> LineItemInput:
    return LineItemInput(
        id=line.id,
        name=line.name,
        quantity=line.quantity,
        unit_price=line.unit_price,
        total_price=line.total_price,
    )


async def _rewrite(
    ctx: ToolContext, receipt: Receipt, lines: list[LineItemInput], total: Decimal
) -> None:
    """Save the receipt's lines and total through the receipt screen's own service."""
    await ReceiptService(repository=ReceiptRepository(ctx.session)).update_receipt(
        receipt.id,
        UpdateReceiptRequest(
            merchant_name=receipt.merchant_name,
            transaction_date=receipt.transaction_date.date() if receipt.transaction_date else None,
            total_amount=total,
            line_items=lines,
        ),
    )


def _target_line(receipt: Receipt, args: LineArgs) -> LineItem | None:
    """The line a correction is about: the one named, or a one-line receipt's only line when
    no line and no new name were said ("it was 59.99"); None adds a line."""
    if args.line:
        named = lines_named(receipt, args.line)
        return named[0] if len(named) == 1 else None
    if not args.name and len(receipt.line_items) == 1:
        return receipt.line_items[0]
    return None


class ChangeLine(Writer):
    """A card correcting a line's name, quantity or price, or adding a line; the receipt's
    total moves by what the line's did, as on the receipt screen (F15.6)."""

    name = "change_line"
    description = (
        "Propose correcting a line of one of the user's receipts — its name, quantity or what "
        "it cost — or adding a line the receipt missed. Find the receipt's id first with the "
        "receipts tool and its lines with receipt_lines."
    )
    args = LineArgs
    card_kind = "line"
    card = LineCard
    form = (
        FormField("target", "target"),
        FormField("name", "text"),
        FormField("amount", "amount"),
    )

    async def check(self, ctx: ToolContext, args: LineArgs) -> str | None:
        receipt = await own_receipt(ctx, args.receipt_id)
        if receipt is None:
            return "no receipt of the user's own with that id"
        if args.line is not None and len(lines_named(receipt, args.line)) != 1:
            names = ", ".join(i.name for i in receipt.line_items)
            return f"no single line named {args.line!r}; the receipt has: {names}"
        if _target_line(receipt, args) is None and (not args.name or args.total is None):
            return "a new line needs its name and what it cost"
        return None

    async def propose(self, ctx: ToolContext, args: LineArgs) -> dict[str, Any]:
        receipt = await own_receipt(ctx, args.receipt_id)
        if receipt is None:
            raise NotFoundError("No such receipt.")
        line = _target_line(receipt, args)
        return {
            "target": receipt_label(receipt),
            "receipt_id": str(receipt.id),
            "line_id": str(line.id) if line else None,
            "name": args.name or (line.name if line else ""),
            "quantity": str(args.quantity or (line.quantity if line else 1)),
            "amount": str(
                args.total if args.total is not None else line.total_price if line else 0
            ),
        }

    async def save(self, ctx: ToolContext, fields: LineCard) -> str:
        receipt = await own_receipt(ctx, str(fields.receipt_id))
        if receipt is None:
            raise NotFoundError("No such receipt.")
        lines = [_input(i) for i in receipt.line_items]
        changed = LineItemInput(
            id=fields.line_id,
            name=fields.name.strip(),
            quantity=fields.quantity,
            unit_price=(fields.amount / fields.quantity).quantize(Decimal("0.01")),
            total_price=fields.amount,
        )
        before = Decimal(0)
        if fields.line_id is None:
            lines.append(changed)
        else:
            index = next((n for n, i in enumerate(lines) if i.id == fields.line_id), None)
            if index is None:
                raise NotFoundError("That line is no longer on the receipt.")
            before = lines[index].total_price
            lines[index] = changed
        total = (receipt.total_amount or Decimal(0)) + fields.amount - before
        await _rewrite(ctx, receipt, lines, total)
        return f"receipt:{receipt.id}"


class RemoveLineArgs(BaseModel):
    """A line to take off a receipt."""

    receipt_id: str = Field(description="The `id` the receipts tool gave the receipt")
    line: str = Field(min_length=1, max_length=120, description="The line, by its name")


class RemoveLineCard(BaseModel):
    """A line's removal as the user approves it."""

    target: str
    receipt_id: uuid.UUID
    line_id: uuid.UUID


class RemoveLine(Writer):
    """A card taking a line off a receipt; the total drops by what the line cost (F15.6)."""

    name = "remove_line"
    description = "Propose taking a line off one of the user's receipts."
    args = RemoveLineArgs
    card_kind = "line_remove"
    card = RemoveLineCard
    form = (FormField("target", "target"),)

    async def check(self, ctx: ToolContext, args: RemoveLineArgs) -> str | None:
        receipt = await own_receipt(ctx, args.receipt_id)
        if receipt is None:
            return "no receipt of the user's own with that id"
        if len(lines_named(receipt, args.line)) != 1:
            names = ", ".join(i.name for i in receipt.line_items)
            return f"no single line named {args.line!r}; the receipt has: {names}"
        return None

    async def propose(self, ctx: ToolContext, args: RemoveLineArgs) -> dict[str, Any]:
        receipt = await own_receipt(ctx, args.receipt_id)
        if receipt is None:
            raise NotFoundError("No such receipt.")
        [line] = lines_named(receipt, args.line)
        return {
            "target": f"{line.name} · {line.total_price} — {receipt_label(receipt)}",
            "receipt_id": str(receipt.id),
            "line_id": str(line.id),
        }

    async def save(self, ctx: ToolContext, fields: RemoveLineCard) -> str:
        receipt = await own_receipt(ctx, str(fields.receipt_id))
        if receipt is None:
            raise NotFoundError("No such receipt.")
        gone = next((i for i in receipt.line_items if i.id == fields.line_id), None)
        if gone is None:
            raise NotFoundError("That line is no longer on the receipt.")
        lines = [_input(i) for i in receipt.line_items if i.id != fields.line_id]
        await _rewrite(ctx, receipt, lines, (receipt.total_amount or Decimal(0)) - gone.total_price)
        return f"receipt:{receipt.id}"


class ConfirmCard(BaseModel):
    """A receipt marked checked, as the user approves it."""

    target: str
    receipt_id: uuid.UUID


class ConfirmReceipt(Writer):
    """A card marking a receipt checked: a possible duplicate kept as a real purchase, and a
    total that disagrees with its lines set to what the lines add up to (A9, A14, D3)."""

    name = "confirm_receipt"
    description = (
        "Propose marking one of the user's receipts as checked: kept though it looked like a "
        "duplicate, and its total set to what its lines add up to."
    )
    args = ReceiptRef
    card_kind = "receipt_confirm"
    card = ConfirmCard
    form = (FormField("target", "target"),)

    async def check(self, ctx: ToolContext, args: ReceiptRef) -> str | None:
        receipt = await own_receipt(ctx, args.receipt_id)
        if receipt is None:
            return "no receipt of the user's own with that id"
        if not review_reasons(receipt):
            return "that receipt does not wait for review"
        if receipt.original_currency and receipt.exchange_rate is None:
            return "it waits for an exchange rate, which comes by itself; nothing to confirm"
        return None

    async def propose(self, ctx: ToolContext, args: ReceiptRef) -> dict[str, Any]:
        receipt = await own_receipt(ctx, args.receipt_id)
        if receipt is None:
            raise NotFoundError("No such receipt.")
        target = receipt_label(receipt)
        if receipt.total_amount is not None and not lines_match_total(
            _lines_sum(receipt), receipt.total_amount
        ):
            target = f"{target} → {_lines_sum(receipt)}"
        return {"target": target, "receipt_id": str(receipt.id)}

    async def save(self, ctx: ToolContext, fields: ConfirmCard) -> str:
        receipt = await own_receipt(ctx, str(fields.receipt_id))
        if receipt is None:
            raise NotFoundError("No such receipt.")
        service = ReceiptService(repository=ReceiptRepository(ctx.session))
        if receipt.possible_duplicate_of_id is not None:
            await service.keep_possible_duplicate(receipt.id)
        if receipt.status == ReceiptStatus.MANUAL_REVIEW:
            await _rewrite(
                ctx, receipt, [_input(i) for i in receipt.line_items], _lines_sum(receipt)
            )
        return f"receipt:{receipt.id}"


class DeleteCard(BaseModel):
    """A receipt's deletion, as the user approves it."""

    target: str
    receipt_id: uuid.UUID


class DeleteReceipt(Writer):
    """A card deleting a receipt with its lines and photos, as from its screen."""

    name = "delete_receipt"
    description = "Propose deleting one of the user's receipts for good, with its photos."
    args = ReceiptRef
    card_kind = "receipt_delete"
    card = DeleteCard
    form = (FormField("target", "target"),)

    async def check(self, ctx: ToolContext, args: ReceiptRef) -> str | None:
        if await own_receipt(ctx, args.receipt_id) is None:
            return "no receipt of the user's own with that id"
        return None

    async def propose(self, ctx: ToolContext, args: ReceiptRef) -> dict[str, Any]:
        receipt = await own_receipt(ctx, args.receipt_id)
        if receipt is None:
            raise NotFoundError("No such receipt.")
        return {"target": receipt_label(receipt), "receipt_id": str(receipt.id)}

    async def save(self, ctx: ToolContext, fields: DeleteCard) -> str:
        service = ReceiptService(
            storage_port=ctx.storage, repository=ReceiptRepository(ctx.session)
        )
        if not await service.delete_receipt(fields.receipt_id):
            raise NotFoundError("No such receipt.")
        return f"deleted:{fields.receipt_id}"


class ReceiptTripArgs(BaseModel):
    """A receipt to put on one of the user's trips, or take off any."""

    receipt_id: str = Field(description="The `id` the receipts tool gave the receipt")
    trip: str | None = Field(
        None, max_length=120, description="The trip, by its name; leave out to take it off"
    )


class ReceiptTripCard(BaseModel):
    """A receipt's trip as the user approves it; no trip takes it off any."""

    target: str
    receipt_id: uuid.UUID
    trip_id: uuid.UUID | None = None
    trip: str = ""


class PlaceOnTrip(Writer):
    """A card putting a receipt on a trip by hand, or taking it off, kept over its dates
    from then on (F20.1)."""

    name = "receipt_trip"
    description = "Propose putting one of the user's receipts on a trip, or taking it off one."
    args = ReceiptTripArgs
    card_kind = "receipt_trip"
    card = ReceiptTripCard
    form = (FormField("target", "target"), FormField("trip", "target"))

    async def check(self, ctx: ToolContext, args: ReceiptTripArgs) -> str | None:
        if await own_receipt(ctx, args.receipt_id) is None:
            return "no receipt of the user's own with that id"
        if args.trip:
            trips = await TripService(ctx.session).list_trips(ctx.user.id)
            found = find_by_name([t.trip for t in trips], args.trip, lambda t: t.name)
            return found.error
        return None

    async def propose(self, ctx: ToolContext, args: ReceiptTripArgs) -> dict[str, Any]:
        receipt = await own_receipt(ctx, args.receipt_id)
        if receipt is None:
            raise NotFoundError("No such receipt.")
        trip = None
        if args.trip:
            trips = await TripService(ctx.session).list_trips(ctx.user.id)
            trip = find_by_name([t.trip for t in trips], args.trip, lambda t: t.name).item
        return {
            "target": receipt_label(receipt),
            "receipt_id": str(receipt.id),
            "trip_id": str(trip.id) if trip else None,
            "trip": trip.name if trip else "",
        }

    async def save(self, ctx: ToolContext, fields: ReceiptTripCard) -> str:
        await TripService(ctx.session).place_receipt(
            fields.receipt_id, as_id(fields.trip_id) if fields.trip_id else None, automatic=False
        )
        return f"receipt:{fields.receipt_id}"


class TripArgs(BaseModel):
    """A trip as the model understood it."""

    name: str = Field(min_length=1, max_length=120, description="What the user calls it")
    kind: TripKind = Field(TripKind.PERSONAL, description="personal, or business for work")
    start: date = Field(description="YYYY-MM-DD")
    end: date = Field(description="YYYY-MM-DD; the start for a one-day trip")
    country: str | None = Field(None, pattern=r"^[A-Za-z]{2}$", description="ISO country code")
    city: str | None = Field(None, max_length=120)
    budget: Amount | None = Field(None, description="Only for a personal trip, if said")


TRIP_KINDS = {"holiday": TripKind.PERSONAL, "work": TripKind.BUSINESS}
"""A trip's kind as the card offers it: its own words, not the account kinds' "personal"."""


class TripCard(BaseModel):
    """A trip as the user approves it."""

    name: str = Field(min_length=1, max_length=120)
    kind: Literal["holiday", "work"]
    start_date: date
    end_date: date
    country: str | None = Field(None, pattern=r"^[A-Za-z]{2}$")
    city: str | None = Field(None, max_length=120)
    budget: Amount | None = None


class AddTrip(Writer):
    """A trip card; its receipts follow its dates once saved (F20.1). Two trips never
    share a day: the service refuses, and the card says so."""

    name = "add_trip"
    description = "Propose a new trip — a holiday, or a business trip — with its dates."
    args = TripArgs
    card_kind = "trip"
    card = TripCard
    form = (
        FormField("name", "text"),
        FormField("kind", "choice", options=tuple(TRIP_KINDS)),
        FormField("start_date", "date"),
        FormField("end_date", "date"),
        FormField("budget", "amount", required=False),
    )

    async def check(self, ctx: ToolContext, args: TripArgs) -> str | None:
        if args.end < args.start:
            return "the trip ends before it starts"
        return None

    async def propose(self, ctx: ToolContext, args: TripArgs) -> dict[str, Any]:
        return {
            "name": args.name,
            "kind": "work" if args.kind is TripKind.BUSINESS else "holiday",
            "start_date": args.start.isoformat(),
            "end_date": args.end.isoformat(),
            "country": args.country.upper() if args.country else None,
            "city": args.city,
            "budget": str(args.budget) if args.budget and args.kind is TripKind.PERSONAL else None,
        }

    async def save(self, ctx: ToolContext, fields: TripCard) -> str:
        trip = await TripService(ctx.session).save(
            ctx.user.id,
            TripDetails(
                kind=TRIP_KINDS[fields.kind],
                name=fields.name,
                country=fields.country,
                city=fields.city,
                start_date=fields.start_date,
                end_date=fields.end_date,
                purpose=None,
                budget=fields.budget if fields.kind == "holiday" else None,
            ),
        )
        return f"trip:{trip.id}"
