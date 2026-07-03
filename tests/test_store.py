"""Behavior of the document store: filing, persistence, and deduplication."""

from __future__ import annotations

from pathlib import Path

from docvault.config import load_config
from docvault.store import DocumentStore
from docvault.types import Document, utc_now


def _doc(doc_id: str, *, filename: str, category: str, content_hash: str) -> Document:
    return Document(
        id=doc_id,
        source_filename=filename,
        category=category,
        summary="a summary",
        page_count=1,
        content_hash=content_hash,
        ingested_at=utc_now(),
    )


def test_files_raw_pdf_under_category_and_persists_metadata(config_file: Path):
    store = DocumentStore(load_config(config_file))
    doc = _doc("id1", filename="q3.pdf", category="research", content_hash="h1")

    stored = store.save(doc, b"%PDF-fake-bytes")

    assert stored.raw_path.exists()
    assert stored.raw_path.parent.name == "research"
    assert stored.raw_path.read_bytes() == b"%PDF-fake-bytes"

    reloaded = store.get("id1")
    assert reloaded is not None
    assert reloaded.document == doc
    assert reloaded.raw_path == stored.raw_path


def test_find_by_hash(config_file: Path):
    store = DocumentStore(load_config(config_file))
    doc = _doc("id1", filename="q3.pdf", category="research", content_hash="hash-A")
    store.save(doc, b"bytes")

    assert store.find_by_hash("hash-A").document == doc
    assert store.find_by_hash("unknown-hash") is None


def test_resaving_same_id_does_not_create_a_second_entry(config_file: Path):
    store = DocumentStore(load_config(config_file))
    doc = _doc("id1", filename="q3.pdf", category="research", content_hash="h1")

    store.save(doc, b"bytes")
    store.save(doc, b"bytes")  # duplicate content, same id

    assert len(store.list()) == 1


def test_filename_collision_between_different_docs_is_disambiguated(config_file: Path):
    store = DocumentStore(load_config(config_file))
    a = _doc("idA", filename="report.pdf", category="research", content_hash="aaaaaaaa11")
    b = _doc("idB", filename="report.pdf", category="research", content_hash="bbbbbbbb22")

    pa = store.save(a, b"A").raw_path
    pb = store.save(b, b"B").raw_path

    assert pa != pb
    assert pa.exists() and pb.exists()
    assert pa.read_bytes() == b"A" and pb.read_bytes() == b"B"


def test_list_returns_all_stored_documents(config_file: Path):
    store = DocumentStore(load_config(config_file))
    store.save(_doc("id1", filename="a.pdf", category="research", content_hash="h1"), b"x")
    store.save(_doc("id2", filename="b.pdf", category="invoices", content_hash="h2"), b"y")

    ids = {s.document.id for s in store.list()}
    assert ids == {"id1", "id2"}


def test_get_unknown_id_returns_none(config_file: Path):
    store = DocumentStore(load_config(config_file))
    assert store.get("nope") is None
