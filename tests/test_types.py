"""Behavior of the domain data types."""

from __future__ import annotations

import dataclasses

import pytest

from docvault.types import Chunk, Citation, Document, utc_now


def _sample_document() -> Document:
    return Document(
        id="doc-1",
        source_filename="q3-report.pdf",
        category="research",
        summary="Quarterly financials for Q3.",
        page_count=12,
        content_hash="abc123",
        ingested_at=utc_now(),
    )


def test_document_round_trips_through_dict():
    doc = _sample_document()

    restored = Document.from_dict(doc.to_dict())

    assert restored == doc


def test_document_to_dict_is_json_friendly():
    doc = _sample_document()

    data = doc.to_dict()

    assert isinstance(data["ingested_at"], str)  # ISO-8601, not a datetime
    assert data["page_count"] == 12


def test_document_is_immutable():
    doc = _sample_document()

    with pytest.raises(dataclasses.FrozenInstanceError):
        doc.category = "invoices"  # type: ignore[misc]


def test_chunk_carries_page_provenance():
    chunk = Chunk(text="churn rose 4%", document_id="doc-1", pages=(4, 5))

    assert chunk.pages == (4, 5)
    with pytest.raises(dataclasses.FrozenInstanceError):
        chunk.text = "tampered"  # type: ignore[misc]


def test_chunk_defaults_to_no_pages():
    chunk = Chunk(text="body", document_id="doc-1")

    assert chunk.pages == ()


def test_citation_shape():
    cite = Citation(
        document_id="doc-1",
        document_name="q3-report.pdf",
        pages=(4,),
        path="/store/raw/research/q3-report.pdf",
    )

    assert cite.document_name == "q3-report.pdf"
    assert cite.pages == (4,)
    with pytest.raises(dataclasses.FrozenInstanceError):
        cite.path = "/elsewhere"  # type: ignore[misc]
