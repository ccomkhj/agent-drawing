"""Behavior of reindex: rebuild from raw PDFs, and embedder-change handling."""

from __future__ import annotations

from docvault.config import load_config
from docvault.index import VectorIndex
from docvault.ingest import Ingestor
from docvault.reindex import reindex
from docvault.retrieval import Retriever
from tests.fakes import FakeEmbedder, FakeLLMClient


def _seed(config_file, make_pdf, tmp_path, embedder) -> None:
    llm = FakeLLMClient(default="research")
    ingestor = Ingestor(load_config(config_file), llm=llm, embedder=embedder)
    ingestor.ingest(make_pdf(tmp_path / "paper.pdf", ["churn analysis for Q3"]))
    ingestor.ingest(make_pdf(tmp_path / "notes.pdf", ["research notes on revenue"]))


def test_reindex_rebuilds_from_raw_after_index_loss(config_file, make_pdf, tmp_path):
    cfg = load_config(config_file)
    _seed(config_file, make_pdf, tmp_path, FakeEmbedder())

    VectorIndex(cfg).reset()  # simulate a lost/corrupt index
    assert VectorIndex(cfg).count() == 0

    n = reindex(cfg, embedder=FakeEmbedder())

    assert n == 2
    assert VectorIndex(cfg).count() > 0
    # searchable again, with provenance intact
    hit = Retriever(cfg, embedder=FakeEmbedder()).search("churn analysis for Q3")[0]
    assert hit.document_name == "paper.pdf"
    assert hit.pages == (1,)


def test_reindex_can_adopt_a_different_embedder(config_file, make_pdf, tmp_path):
    cfg = load_config(config_file)
    _seed(config_file, make_pdf, tmp_path, FakeEmbedder(model_id_value="a", dimension_value=8))

    # A different embedding model/dimension would normally mismatch — reindex resets.
    reindex(cfg, embedder=FakeEmbedder(model_id_value="b", dimension_value=16))

    assert VectorIndex(cfg).embedding_metadata() == {"model_id": "b", "dimension": 16}
    assert VectorIndex(cfg).count() > 0


def test_reindex_empty_store_is_zero(config_file):
    assert reindex(load_config(config_file), embedder=FakeEmbedder()) == 0
