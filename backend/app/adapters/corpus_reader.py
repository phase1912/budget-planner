"""A stand-in reader that answers from the receipts corpus (F0.11.2).

The browser suite and local checks need receipt reading that is deterministic, free and
offline. Each corpus case (``evaluation/corpus/<country>/<case>/case.json``, F0.11.3)
says what its files are; this reader recognises a file by its bytes and answers with
that case, through the same ports as the model's reader (LSP). It is never selected in
staging or production (``Settings``).
"""

import hashlib
import json
import logging
from collections.abc import Sequence
from functools import cached_property
from pathlib import Path
from typing import Any

from app.models.category import Category
from app.schemas.extraction import ExtractedLineItem, ExtractedReceipt

logger = logging.getLogger(__name__)

CASE_FILE = "case.json"
FILE_TYPES = {".jpg", ".jpeg", ".png", ".heic", ".pdf"}
DOCUMENT_KINDS = {"receipt": "receipt", "money_received": "income"}
"""How a corpus document is told to today's reader; money sent is not a receipt yet."""


def file_key(content: bytes) -> str:
    """The key a file is known by in the corpus: its SHA-256."""
    return hashlib.sha256(content).hexdigest()


def case_files(folder: Path, case: dict[str, Any]) -> list[Path]:
    """The case's files in order: those it names, else every photo or PDF in its folder."""
    named = case.get("files")
    if named:
        return [folder / name for name in named]
    return sorted(p for p in folder.iterdir() if p.suffix.lower() in FILE_TYPES)


class CorpusCases:
    """Every case under a folder, found by any one of its files' bytes."""

    def __init__(self, root: Path) -> None:
        self.root = root

    @cached_property
    def by_file(self) -> dict[str, dict[str, Any]]:
        """Each file's key to the case it belongs to; read once, on first use."""
        found: dict[str, dict[str, Any]] = {}
        if not self.root.is_dir():
            logger.warning("The receipts corpus %s does not exist", self.root)
            return found
        for path in sorted(self.root.rglob(CASE_FILE)):
            case = json.loads(path.read_text(encoding="utf-8"))
            for file in case_files(path.parent, case):
                found[file_key(file.read_bytes())] = case
        return found

    def find(self, images: Sequence[bytes]) -> dict[str, Any] | None:
        """The case any of these files belongs to, or None for a file the corpus lacks."""
        for image in images:
            case = self.by_file.get(file_key(image))
            if case is not None:
                return case
        return None


def as_extraction(document: dict[str, Any]) -> ExtractedReceipt:
    """A corpus document as the reader's answer would be, read with full confidence."""
    kind = DOCUMENT_KINDS.get(document.get("kind", "receipt"), "other")
    lines = [
        ExtractedLineItem(
            name=line["name"],
            quantity=str(line.get("quantity", "1")),
            unit_price=str(line.get("unit_price", line["total"])),
            total_price=str(line["total"]),
            confidence=100,
        )
        for line in document.get("lines", [])
    ]
    return ExtractedReceipt(
        merchant_name=document.get("merchant"),
        merchant_name_confidence=100,
        transaction_date=document.get("date"),
        transaction_date_confidence=100 if document.get("date") else 0,
        currency=document.get("currency"),
        line_items=lines,
        receipt_total=document.get("total"),
        receipt_total_confidence=100 if document.get("total") else 0,
        document_kind=kind,
        is_receipt_confidence=100 if kind != "other" else 0,
    )


NOT_KNOWN = ExtractedReceipt(document_kind="other", is_receipt_confidence=0)
"""The answer for a file the corpus does not hold: not a receipt, as the model would say."""


class CorpusReader:
    """Implements ``ReceiptParserPort`` and ``ReceiptRecheckerPort`` from the corpus.

    Today's reader takes one receipt per upload, so a case's first document is the
    answer; cases with several documents describe what the one-door reader (F21.16)
    must find, and the browser suite marks them as expected to fail until then.
    """

    def __init__(self, cases: CorpusCases) -> None:
        self.cases = cases

    async def parse(
        self, images: list[bytes], *, mime_types: list[str] | None = None
    ) -> ExtractedReceipt:
        """The case's first document, or "not a receipt" for an unknown file."""
        case = self.cases.find(images)
        if case is None or not case.get("documents"):
            return NOT_KNOWN.model_copy()
        return as_extraction(case["documents"][0])

    async def recheck(
        self, images: list[bytes], *, mime_types: list[str], reading: ExtractedReceipt
    ) -> ExtractedReceipt:
        """The same answer again: the corpus never changes its mind."""
        return await self.parse(images, mime_types=mime_types)


class CorpusCategoriser:
    """Implements ``ItemCategoriserPort``: each line in the category its case names.

    Lines are matched to the case's by name; a line whose case names no category, or one
    the user does not have, is left for review, as the model leaves what it cannot place.
    """

    def __init__(self, cases: CorpusCases) -> None:
        self.cases = cases

    async def categorise_items(
        self, items: list[ExtractedLineItem], categories: Sequence[Category]
    ) -> list[ExtractedLineItem]:
        """Fill each item's category from its case; never raises."""
        named = {
            line["name"]: line.get("category")
            for case in self.cases.by_file.values()
            for document in case.get("documents", [])
            for line in document.get("lines", [])
        }
        by_name = {c.name.lower(): c for c in categories}
        for item in items:
            wanted = named.get(item.name)
            category = by_name.get(wanted.lower()) if wanted else None
            if category is not None:
                item.category_id = category.id
                item.category_name = category.name
                item.category_confidence = 100
        return items
