"""Behavior of chunking: page provenance and windowing."""

from __future__ import annotations

from docvault.chunking import chunk_document
from docvault.parsing import PageText, ParsedDocument


def _parsed(pages: list[tuple[int, str]]) -> ParsedDocument:
    return ParsedDocument(
        pages=tuple(PageText(number=n, text=t) for n, t in pages),
        content_hash="h",
    )


def test_chunks_carry_page_provenance_and_document_id():
    parsed = _parsed([(1, "alpha"), (2, "beta")])

    chunks = chunk_document(parsed, "doc-1")

    assert [c.text for c in chunks] == ["alpha", "beta"]
    assert chunks[0].pages == (1,)
    assert chunks[1].pages == (2,)
    assert all(c.document_id == "doc-1" for c in chunks)


def test_long_page_splits_into_multiple_overlapping_chunks_same_page():
    long_text = "x" * 2000
    parsed = _parsed([(3, long_text)])

    chunks = chunk_document(parsed, "doc-1", max_chars=800, overlap=150)

    assert len(chunks) > 1
    assert all(c.pages == (3,) for c in chunks)  # provenance stays on page 3
    assert all(len(c.text) <= 800 for c in chunks)


def test_empty_pages_are_skipped():
    parsed = _parsed([(1, "   "), (2, "real content"), (3, "")])

    chunks = chunk_document(parsed, "doc-1")

    assert [c.pages for c in chunks] == [(2,)]
