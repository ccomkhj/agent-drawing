"""Behavior of retrieval and the three tool operations.

Fake embedder (deterministic vectors) + real temp-dir index seeded via ingest.
Querying with a chunk's own text makes it the nearest neighbour deterministically.
"""

from __future__ import annotations

from pathlib import Path

from docvault.config import load_config
from docvault.ingest import Ingestor
from docvault.retrieval import Retriever
from tests.fakes import FakeEmbedder, FakeLLMClient


def _seed(config_file, make_pdf, tmp_path) -> None:
    """Ingest one research PDF and one invoices PDF."""
    llm = FakeLLMClient(responses=["summary", "research", "summary", "invoices"])
    ingestor = Ingestor(load_config(config_file), llm=llm, embedder=FakeEmbedder())
    ingestor.ingest(make_pdf(tmp_path / "paper.pdf", ["churn analysis for Q3"]))
    ingestor.ingest(make_pdf(tmp_path / "bill.pdf", ["invoice total due amount"]))


def _retriever(config_file) -> Retriever:
    return Retriever(load_config(config_file), embedder=FakeEmbedder())


def test_search_returns_relevant_chunk_with_provenance(config_file, make_pdf, tmp_path):
    _seed(config_file, make_pdf, tmp_path)

    hits = _retriever(config_file).search("churn analysis for Q3")

    assert hits
    top = hits[0]
    assert "churn" in top.text
    assert top.document_name == "paper.pdf"
    assert top.pages == (1,)
    assert top.path.endswith("paper.pdf")


def test_search_can_narrow_by_category(config_file, make_pdf, tmp_path):
    _seed(config_file, make_pdf, tmp_path)

    hits = _retriever(config_file).search("anything", category="invoices", k=10)

    assert hits
    assert all(h.document_name == "bill.pdf" for h in hits)


def test_search_hit_builds_a_citation(config_file, make_pdf, tmp_path):
    _seed(config_file, make_pdf, tmp_path)

    hit = _retriever(config_file).search("churn analysis for Q3")[0]
    cite = hit.citation()

    assert cite.document_name == "paper.pdf"
    assert cite.pages == (1,)


def test_search_on_empty_index_returns_nothing(config_file):
    assert _retriever(config_file).search("anything") == []


def test_list_categories_reflects_taxonomy(config_file):
    assert _retriever(config_file).list_categories() == ["invoices", "research"]


def test_read_full_pdf_returns_text(config_file, make_pdf, tmp_path):
    _seed(config_file, make_pdf, tmp_path)
    retriever = _retriever(config_file)
    doc_id = retriever.search("churn analysis for Q3")[0].document_id

    text = retriever.read_full_pdf(doc_id)

    assert text is not None and "churn" in text


def test_read_full_pdf_unknown_id_returns_none(config_file):
    assert _retriever(config_file).read_full_pdf("nope") is None
