"""A business trip's settlement for the employer, as PDF or CSV (F20.5, BRD N6).

The settlement is what an employee hands in after a business trip: the trip, what was
spent by kind and by currency paid, the per diem worked out under the Polish rules
(ADR-0018), the advance already received, and what is still owed — expenses + per diem minus
the advance. The PDF carries every receipt's photo on the pages after the summary. Both are
written in the user's language; English is the fallback.
"""

import csv
import io
import json
import logging
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from functools import cache
from pathlib import Path

from fpdf import FPDF
from PIL import Image, UnidentifiedImageError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.retention import photos_removed
from app.domain.trips import ExpenseKind, Settlement, TripKind, TripSpending, settle
from app.models.receipt import Receipt, ReceiptChannel, ReceiptStatus
from app.models.trip import Trip
from app.models.user import User
from app.ports.exchange_rates import ExchangeRatePort
from app.ports.storage import StoragePort, receipt_object_name
from app.services.trip import PerDiem, TripService, kind_of, trip_spending

logger = logging.getLogger(__name__)

FONTS = Path(__file__).resolve().parent.parent / "assets" / "fonts"

MINUS = "\u2212"
DASH = "\u2013"


@cache
def _texts() -> dict[str, dict[str, str]]:
    path = FONTS.parent / "settlement_text.json"
    texts: dict[str, dict[str, str]] = json.loads(path.read_text(encoding="utf-8"))
    return texts


def text_for(language: str | None) -> dict[str, str]:
    """The settlement's words in `language`, English for any language not kept."""
    texts = _texts()
    return texts.get(language or "en", texts["en"])


@dataclass(frozen=True)
class TripSettlement:
    """Everything a business trip's settlement shows, gathered once for either format."""

    trip: Trip
    employee: str
    currency: str
    receipts: list[Receipt]
    spending: TripSpending
    per_diem: PerDiem | None
    sums: Settlement


async def gather(
    session: AsyncSession, user: User, trip_id: str, rates: ExchangeRatePort | None
) -> TripSettlement:
    """A business trip's settlement for its owner (F20.5).

    Raises NotFoundError for a trip not the user's (N2), and ValueError for a personal
    trip, which is the user's own money and has nothing to settle.
    """
    service = TripService(session)
    summary, receipts, _ = await service.get(user.id, uuid.UUID(trip_id))
    if summary.trip.kind is not TripKind.BUSINESS:
        raise ValueError("Only a business trip is settled with the employer")
    per_diem = await service.per_diem_of(summary.trip, rates, user.currency)
    read = [r for r in receipts if r.status is ReceiptStatus.PARSED]
    return TripSettlement(
        trip=summary.trip,
        employee=f"{user.first_name} {user.last_name}".strip(),
        currency=user.currency,
        receipts=read,
        spending=trip_spending(read, user.currency),
        per_diem=per_diem,
        sums=settle(
            summary.total,
            per_diem is not None,
            per_diem.total_account if per_diem else None,
            summary.trip.advance,
        ),
    )


def _money(amount: Decimal | None) -> str:
    return "—" if amount is None else f"{amount:.2f}"


def _name(receipt: Receipt, words: dict[str, str], today: date | None = None) -> str:
    """The receipt's merchant, marked when it has no picture to show.

    Typed in without a receipt (F20.5), or its photo removed after 90 days (F17.9.3):
    the settlement still counts it, and says why no page shows it.
    """
    name = receipt.merchant_name or words["unknown"]
    if receipt.channel is ReceiptChannel.MANUAL:
        return f"{name} ({words['no_receipt']})"
    if _photos_gone(receipt, today or datetime.now(UTC).date()):
        return f"{name} ({words['photo_removed']})"
    return name


def _photos_gone(receipt: Receipt, today: date) -> bool:
    return photos_removed(receipt.created_at, bool(receipt.file_ids), today)


def _day(receipt: Receipt) -> date:
    return (receipt.transaction_date or receipt.created_at).date()


def _equation(data: TripSettlement) -> str:
    """The sum as the employer checks it: "612.40 + 207.00 - 500.00 = 319.40 PLN"."""
    sums = data.sums
    parts = [_money(sums.expenses)]
    if sums.per_diem is not None:
        parts.append(f"+ {_money(sums.per_diem)}")
    if sums.advance:
        parts.append(f"{MINUS} {_money(sums.advance)}")
    return f"{' '.join(parts)} = {_money(sums.to_reimburse)} {data.currency}"


def settlement_csv(data: TripSettlement, language: str | None) -> bytes:
    """The settlement as CSV: each receipt, each per diem day, then the sums (F20.5)."""
    words = text_for(language)
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(
        [
            words["section"],
            words["date"],
            words["merchant"],
            words["kind"],
            words["amount"],
            words["currency"],
            words["paid"],
            words["paid_currency"],
        ]
    )
    for receipt in data.receipts:
        amount = sum((item.total_price for item in receipt.line_items), Decimal(0))
        foreign = receipt.original_currency and receipt.original_total is not None
        writer.writerow(
            [
                words["receipts"],
                _day(receipt).isoformat(),
                _safe(_name(receipt, words)),
                words[kind_of(receipt).value],
                _money(amount),
                data.currency,
                _money(receipt.original_total) if foreign else _money(amount),
                receipt.original_currency if foreign else data.currency,
            ]
        )
    if data.per_diem:
        for part in data.per_diem.parts:
            for day in part.days:
                writer.writerow(
                    [
                        words["per_diem"],
                        "",
                        f"{words['day']} {day.number} ({day.rule})",
                        "",
                        "",
                        "",
                        _money(day.due),
                        part.rate.currency,
                    ]
                )
    sums = data.sums
    sums_rows: list[tuple[str, Decimal | None]] = [
        (words["expenses"], sums.expenses),
        (words["per_diem"], sums.per_diem),
        (words["advance"], sums.advance),
        (words["to_reimburse"], sums.to_reimburse),
    ]
    for label, figure in sums_rows:
        writer.writerow([label, "", "", "", _money(figure), data.currency, "", ""])
    return buffer.getvalue().encode("utf-8")


def _safe(text: str) -> str:
    """A cell a spreadsheet will not run as a formula."""
    return f"'{text}" if text.startswith(("=", "+", "-", "@", "\t", "\r")) else text


class _Pdf(FPDF):
    def __init__(self) -> None:
        super().__init__(format="A4")
        self.add_font("DejaVu", "", str(FONTS / "DejaVuSans.ttf"))
        self.add_font("DejaVu", "B", str(FONTS / "DejaVuSans-Bold.ttf"))
        self.set_auto_page_break(auto=True, margin=15)
        self.set_margins(15, 15, 15)

    def heading(self, text: str, size: int = 13) -> None:
        self.set_font("DejaVu", "B", size)
        self.ln(2)
        self.multi_cell(0, 8, text, new_x="LMARGIN", new_y="NEXT")

    def line_of(self, label: str, value: str, bold: bool = False) -> None:
        self.set_font("DejaVu", "B" if bold else "", 10)
        self.cell(70, 6, label)
        self.multi_cell(0, 6, value, new_x="LMARGIN", new_y="NEXT")


def _photo(content: bytes) -> bytes | None:
    """A photo as JPEG the PDF can carry, or None for a file that is not a picture."""
    try:
        import pillow_heif

        pillow_heif.register_heif_opener()  # type: ignore[attr-defined]
        with Image.open(io.BytesIO(content)) as image:
            image.thumbnail((1600, 1600))
            out = io.BytesIO()
            image.convert("RGB").save(out, format="JPEG", quality=80)
            return out.getvalue()
    except (UnidentifiedImageError, OSError, ValueError):
        return None


def settlement_pdf(
    data: TripSettlement, language: str | None, photos: Sequence[tuple[Receipt, list[bytes]]]
) -> bytes:
    """The settlement as one PDF: the summary, then each receipt's photos (F20.5).

    `photos` pairs each receipt with its stored files; a file that is not a picture is
    noted on its page instead of failing the whole settlement.
    """
    words = text_for(language)
    trip = data.trip
    pdf = _Pdf()
    pdf.add_page()
    pdf.heading(words["title"], 16)
    pdf.line_of(words["employee"], data.employee)
    pdf.line_of(words["trip"], trip.name)
    place = ", ".join(p for p in [trip.city, trip.country] if p)
    if place:
        pdf.line_of(words["destination"], place)
    pdf.line_of(words["dates"], f"{trip.start_date.isoformat()} {DASH} {trip.end_date.isoformat()}")
    if trip.purpose:
        pdf.line_of(words["purpose"], trip.purpose)

    pdf.heading(words["by_kind"])
    for kind in ExpenseKind:
        pdf.line_of(words[kind.value], f"{_money(data.spending.by_kind[kind])} {data.currency}")
    if any(c != data.currency for c in data.spending.by_currency):
        pdf.heading(words["by_currency"])
        for currency, total in sorted(data.spending.by_currency.items()):
            pdf.line_of(currency, _money(total))

    pdf.heading(words["per_diem"])
    if data.per_diem is None:
        pdf.line_of("", words["per_diem_none"])
    else:
        for part in data.per_diem.parts:
            pdf.line_of(
                f"{part.country} · {part.rate.amount} {part.rate.currency}",
                f"{_money(part.total)} {part.rate.currency}",
                bold=True,
            )
            for day in part.days:
                meals = (
                    f" {MINUS} {_money(day.reduction)} ({day.meals_rule})" if day.reduction else ""
                )
                pdf.line_of(
                    f"  {words['day']} {day.number}: {day.hours} h",
                    f"{_money(day.amount)}{meals} = {_money(day.due)} · {day.rule}",
                )
        claimed = data.per_diem.total_account
        pdf.line_of(
            words["per_diem"],
            f"{_money(claimed)} {data.currency}" if claimed is not None else words["not_converted"],
            bold=True,
        )
        pdf.set_font("DejaVu", "", 8)
        pdf.multi_cell(0, 5, words["per_diem_rule"], new_x="LMARGIN", new_y="NEXT")

    pdf.heading(words["receipts"])
    for receipt in data.receipts:
        amount = sum((item.total_price for item in receipt.line_items), Decimal(0))
        pdf.line_of(
            f"{_day(receipt).isoformat()} {_name(receipt, words)}"[:48],
            f"{_money(amount)} {data.currency} · {words[kind_of(receipt).value]}",
        )

    pdf.heading(words["to_reimburse"] if (data.sums.to_reimburse or 0) >= 0 else words["to_return"])
    pdf.line_of(words["expenses"], f"{_money(data.sums.expenses)} {data.currency}")
    if data.sums.per_diem is not None:
        pdf.line_of(words["per_diem"], f"{_money(data.sums.per_diem)} {data.currency}")
    pdf.line_of(words["advance"], f"{_money(data.sums.advance)} {data.currency}")
    pdf.line_of(words["to_reimburse"], _equation(data), bold=True)

    for receipt, files in photos:
        for content in files:
            pdf.add_page()
            pdf.heading(
                f"{_day(receipt).isoformat()} · {receipt.merchant_name or words['unknown']}", 11
            )
            picture = _photo(content)
            if picture is None:
                pdf.line_of("", words["no_photo"])
                continue
            pdf.image(io.BytesIO(picture), x=15, w=pdf.epw, keep_aspect_ratio=True, h=pdf.eph - 20)
    return bytes(pdf.output())


async def receipt_photos(
    storage: StoragePort, receipts: Sequence[Receipt]
) -> list[tuple[Receipt, list[bytes]]]:
    """Each receipt's stored files, read from its owner's prefix; a missing one is skipped.

    Photos storage has removed after 90 days are not asked for: no page, no placeholder.
    """
    found = []
    today = datetime.now(UTC).date()
    for receipt in receipts:
        files = []
        for file_id in [] if _photos_gone(receipt, today) else receipt.file_ids:
            try:
                files.append(
                    await storage.download_file(receipt_object_name(receipt.user_id, file_id))
                )
            except Exception:
                logger.warning("Photo %s of receipt %s could not be read", file_id, receipt.id)
        found.append((receipt, files))
    return found
