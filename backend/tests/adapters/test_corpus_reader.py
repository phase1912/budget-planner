"""Tests for the corpus-backed receipt reader, categoriser and factory (F0.11.2)."""

import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.adapters import reading_factory
from app.adapters.categorisation_agent import ItemCategoriserAdapter
from app.adapters.corpus_reader import (
    CorpusCases,
    CorpusCategoriser,
    CorpusReader,
    case_files,
    file_key,
)
from app.adapters.vision_agent import VisionAgentAdapter
from app.models.category import Category
from app.schemas.extraction import ExtractedLineItem


def test_corpus_cases_warns_and_returns_empty_when_directory_is_missing(
    tmp_path: Path,
) -> None:
    """A missing corpus folder yields no cases without crashing."""
    cases = CorpusCases(tmp_path / "nonexistent")
    assert cases.by_file == {}
    assert cases.find([b"unknown"]) is None


def test_case_files_discovers_supported_files_when_not_explicitly_named(
    tmp_path: Path,
) -> None:
    """When case.json omits `files`, supported image and PDF files are picked in order."""
    (tmp_path / "b.png").write_bytes(b"png-bytes")
    (tmp_path / "a.jpg").write_bytes(b"jpg-bytes")
    (tmp_path / "notes.txt").write_text("ignored", encoding="utf-8")

    found = case_files(tmp_path, {})

    assert [p.name for p in found] == ["a.jpg", "b.png"]


def test_case_files_respects_explicit_file_list(tmp_path: Path) -> None:
    """When case.json lists `files`, only those files in that order are returned."""
    (tmp_path / "first.jpg").write_bytes(b"1")
    (tmp_path / "second.jpg").write_bytes(b"2")

    found = case_files(tmp_path, {"files": ["second.jpg", "first.jpg"]})

    assert [p.name for p in found] == ["second.jpg", "first.jpg"]


@pytest.mark.asyncio
async def test_corpus_reader_returns_first_document_for_known_file_and_not_known_otherwise() -> (
    None
):
    """Known corpus files return their extraction; unknown files return `other` (F0.11.2)."""
    corpus_root = Path(__file__).resolve().parents[2] / "evaluation" / "corpus"
    cases = CorpusCases(corpus_root)
    reader = CorpusReader(cases)

    first_case_photo = next(corpus_root.rglob("*.jpg")).read_bytes()
    known = await reader.parse([first_case_photo], mime_types=["image/jpeg"])
    rechecked = await reader.recheck([first_case_photo], mime_types=["image/jpeg"], reading=known)
    unknown = await reader.parse([b"not-in-corpus"], mime_types=["image/jpeg"])

    assert known.document_kind in {"receipt", "income"}
    assert known.is_receipt_confidence == 100
    assert rechecked == known
    assert unknown.document_kind == "other"
    assert unknown.is_receipt_confidence == 0


@pytest.mark.asyncio
async def test_corpus_categoriser_assigns_matching_categories_and_leaves_unknown(
    tmp_path: Path,
) -> None:
    """Lines named in the corpus get the user's matching category; unknown ones stay blank."""
    (tmp_path / "r.jpg").write_bytes(b"img")
    (tmp_path / "case.json").write_text(
        '{"files": ["r.jpg"], "documents": [{"lines": '
        '[{"name": "Milk", "total": "5.00", "category": "Groceries"}]}]}',
        encoding="utf-8",
    )
    categoriser = CorpusCategoriser(CorpusCases(tmp_path))

    groceries = Category(id=uuid.uuid4(), name="Groceries")
    items = [
        ExtractedLineItem(name="Milk", quantity="1", unit_price="5.00", total_price="5.00"),
        ExtractedLineItem(name="Unknown", quantity="1", unit_price="10.00", total_price="10.00"),
    ]

    result = await categoriser.categorise_items(items, [groceries])

    assert result[0].category_id == groceries.id
    assert result[0].category_name == "Groceries"
    assert result[0].category_confidence == 100
    assert result[1].category_id is None


def test_reading_factory_selects_corpus_or_model_from_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`receipt_reader` and `item_categoriser` switch between corpus and model (F0.11.2)."""
    reading_factory._cases.clear()

    corpus_settings = MagicMock(reading_engine="corpus", reading_corpus_dir="evaluation/corpus")
    with patch.object(reading_factory, "get_settings", return_value=corpus_settings):
        parser, rechecker = reading_factory.receipt_reader()
        categoriser = reading_factory.item_categoriser()
        assert isinstance(parser, CorpusReader)
        assert parser is rechecker
        assert isinstance(categoriser, CorpusCategoriser)

    model_settings = MagicMock(reading_engine="model", reading_corpus_dir="evaluation/corpus")
    with (
        patch.object(reading_factory, "get_settings", return_value=model_settings),
        patch.object(reading_factory, "agent_from_settings", return_value=MagicMock()),
    ):
        parser, rechecker = reading_factory.receipt_reader()
        categoriser = reading_factory.item_categoriser()
        assert isinstance(parser, VisionAgentAdapter)
        assert parser is rechecker
        assert isinstance(categoriser, ItemCategoriserAdapter)


def test_file_key_returns_sha256_hex_digest() -> None:
    """Files are indexed by their deterministic SHA-256 hex digest."""
    assert len(file_key(b"sample")) == 64
