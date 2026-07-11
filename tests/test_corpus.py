"""Behavior of the Corpus: the store↔index pairing behind one interface.

Real temp-dir Chroma + real filesystem store + fake (deterministic) embedder.
Querying with a chunk's own text makes it the nearest neighbour deterministically.
Single-module behaviors live in test_store.py / test_index.py (internal seams);
this file owns everything that only exists at the pairing.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from chromadb.api.client import SharedSystemClient

from docvault.config import load_config
from docvault.corpus import Corpus
from docvault.errors import DocVaultError
from docvault.parsing import parse_pdf
from docvault.types import Document, utc_now
from tests.fakes import FakeEmbedder


def _corpus(config_file: Path, embedder=None) -> Corpus:
    return Corpus(load_config(config_file), embedder=embedder or FakeEmbedder())


def _add(corpus: Corpus, path: Path, *, category: str):
    """Ingest one PDF straight through Corpus.add (parse → build Document → add)."""
    parsed = parse_pdf(path)
    doc = Document(
        id=parsed.content_hash[:16],
        source_filename=path.name,
        category=category,
        summary="a summary",
        page_count=parsed.page_count,
        content_hash=parsed.content_hash,
        ingested_at=utc_now(),
    )
    return corpus.add(doc, path.read_bytes(), parsed)


def _lose_index(cfg) -> None:
    """Simulate a lost/corrupt index: drop it on disk and evict Chroma's
    in-process client cache (which otherwise keeps the deleted data live)."""
    shutil.rmtree(cfg.index_dir)
    SharedSystemClient.clear_system_cache()


def _seed(corpus: Corpus, make_pdf, tmp_path) -> None:
    _add(corpus, make_pdf(tmp_path / "paper.pdf", ["churn analysis for Q3"]), category="research")
    _add(corpus, make_pdf(tmp_path / "bill.pdf", ["invoice total due amount"]), category="invoices")


# --- add writes both halves ---------------------------------------------------


def test_add_files_the_document_and_makes_it_searchable(config_file, make_pdf, tmp_path):
    corpus = _corpus(config_file)
    _add(corpus, make_pdf(tmp_path / "paper.pdf", ["churn analysis for Q3"]), category="research")

    # store side: the Document is listed
    assert [s.document.source_filename for s in corpus.documents()] == ["paper.pdf"]
    # index side: it's searchable, with provenance
    hits = corpus.search("churn analysis for Q3")
    assert hits and hits[0].document_name == "paper.pdf" and hits[0].pages == (1,)


# --- search -------------------------------------------------------------------


def test_search_returns_relevant_chunk_with_provenance(config_file, make_pdf, tmp_path):
    corpus = _corpus(config_file)
    _seed(corpus, make_pdf, tmp_path)

    top = corpus.search("churn analysis for Q3")[0]

    assert "churn" in top.text
    assert top.document_name == "paper.pdf"
    assert top.pages == (1,)
    assert top.path.endswith("paper.pdf")


def test_search_can_narrow_by_category(config_file, make_pdf, tmp_path):
    corpus = _corpus(config_file)
    _seed(corpus, make_pdf, tmp_path)

    hits = corpus.search("anything", category="invoices", k=10)

    assert hits
    assert all(h.document_name == "bill.pdf" for h in hits)


def test_search_hit_builds_a_citation(config_file, make_pdf, tmp_path):
    corpus = _corpus(config_file)
    _seed(corpus, make_pdf, tmp_path)

    cite = corpus.search("churn analysis for Q3")[0].citation()

    assert cite.document_name == "paper.pdf"
    assert cite.pages == (1,)


def test_search_on_empty_index_returns_nothing(config_file):
    assert _corpus(config_file).search("anything") == []


def test_search_skips_a_hit_whose_document_is_gone(config_file, make_pdf, tmp_path):
    """Drift contract: a chunk whose Document is missing is skipped, not raised."""
    cfg = load_config(config_file)
    corpus = Corpus(cfg, embedder=FakeEmbedder())
    stored = _add(corpus, make_pdf(tmp_path / "paper.pdf", ["churn analysis for Q3"]), category="research")

    # remove the store metadata, leaving the chunk orphaned in the index
    (cfg.meta_dir / f"{stored.document.id}.json").unlink()

    assert corpus.search("churn analysis for Q3") == []


# --- read_full ----------------------------------------------------------------


def test_read_full_returns_text(config_file, make_pdf, tmp_path):
    corpus = _corpus(config_file)
    stored = _add(corpus, make_pdf(tmp_path / "paper.pdf", ["churn analysis for Q3"]), category="research")

    text = corpus.read_full(stored.document.id)

    assert text is not None and "churn" in text


def test_read_full_unknown_id_returns_none(config_file):
    assert _corpus(config_file).read_full("nope") is None


# --- documents / find_by_hash -------------------------------------------------


def test_documents_lists_all_stored(config_file, make_pdf, tmp_path):
    corpus = _corpus(config_file)
    _seed(corpus, make_pdf, tmp_path)

    names = {s.document.source_filename for s in corpus.documents()}
    assert names == {"paper.pdf", "bill.pdf"}


def test_find_by_hash(config_file, make_pdf, tmp_path):
    corpus = _corpus(config_file)
    stored = _add(corpus, make_pdf(tmp_path / "paper.pdf", ["churn analysis for Q3"]), category="research")

    assert corpus.find_by_hash(stored.document.content_hash).document == stored.document
    assert corpus.find_by_hash("unknown-hash") is None


# --- rebuild ------------------------------------------------------------------


def test_rebuild_heals_a_lost_index(config_file, make_pdf, tmp_path):
    cfg = load_config(config_file)
    corpus = Corpus(cfg, embedder=FakeEmbedder())
    _seed(corpus, make_pdf, tmp_path)

    _lose_index(cfg)
    assert Corpus(cfg, embedder=FakeEmbedder()).search("churn analysis for Q3") == []

    n = Corpus(cfg, embedder=FakeEmbedder()).rebuild()

    assert n == 2
    healed = Corpus(cfg, embedder=FakeEmbedder()).search("churn analysis for Q3")[0]
    assert healed.document_name == "paper.pdf"
    assert healed.pages == (1,)


def test_rebuild_adopts_a_different_embedder(config_file, make_pdf, tmp_path):
    cfg = load_config(config_file)
    _seed(
        Corpus(cfg, embedder=FakeEmbedder(model_id_value="a", dimension_value=8)),
        make_pdf,
        tmp_path,
    )

    # A different model/dimension would normally mismatch — rebuild resets first.
    corpus_b = Corpus(cfg, embedder=FakeEmbedder(model_id_value="b", dimension_value=16))
    assert corpus_b.rebuild() == 2

    assert corpus_b.search("churn analysis for Q3")[0].document_name == "paper.pdf"


def test_rebuild_empty_corpus_is_zero(config_file):
    assert _corpus(config_file).rebuild() == 0


# --- embedder is optional for read-only ops -----------------------------------


def test_read_only_ops_work_without_an_embedder(config_file, make_pdf, tmp_path):
    # Seed with an embedder, then reopen the Corpus with none (the `list` path).
    _seed(_corpus(config_file), make_pdf, tmp_path)

    reader = Corpus(load_config(config_file))  # no embedder

    assert {s.document.source_filename for s in reader.documents()} == {"paper.pdf", "bill.pdf"}


def test_embedding_ops_without_an_embedder_raise(config_file):
    reader = Corpus(load_config(config_file))  # no embedder

    with pytest.raises(DocVaultError):
        reader.search("anything")
