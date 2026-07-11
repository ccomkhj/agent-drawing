"""Behavior of the reindex entry point: rebuild from raw PDFs, and embedder-change
handling. The rebuild mechanics are covered at the Corpus interface (test_corpus);
here we exercise the free `reindex()` wrapper the CLI uses, asserting through
Corpus."""

from __future__ import annotations

import shutil

from chromadb.api.client import SharedSystemClient

from docvault.config import load_config
from docvault.corpus import Corpus
from docvault.ingest import Ingestor
from docvault.reindex import reindex
from tests.fakes import FakeEmbedder, FakeLLMClient


def _seed(config_file, make_pdf, tmp_path, embedder) -> None:
    llm = FakeLLMClient(default="research")
    ingestor = Ingestor(load_config(config_file), llm=llm, embedder=embedder)
    ingestor.ingest(make_pdf(tmp_path / "paper.pdf", ["churn analysis for Q3"]))
    ingestor.ingest(make_pdf(tmp_path / "notes.pdf", ["research notes on revenue"]))


def test_reindex_rebuilds_from_raw_after_index_loss(config_file, make_pdf, tmp_path):
    cfg = load_config(config_file)
    _seed(config_file, make_pdf, tmp_path, FakeEmbedder())

    # simulate a lost/corrupt index: drop it on disk and evict Chroma's
    # in-process client cache (which otherwise keeps the deleted data live)
    shutil.rmtree(cfg.index_dir)
    SharedSystemClient.clear_system_cache()
    assert Corpus(cfg, embedder=FakeEmbedder()).search("churn analysis for Q3") == []

    n = reindex(cfg, embedder=FakeEmbedder())

    assert n == 2
    # searchable again, with provenance intact
    hit = Corpus(cfg, embedder=FakeEmbedder()).search("churn analysis for Q3")[0]
    assert hit.document_name == "paper.pdf"
    assert hit.pages == (1,)


def test_reindex_can_adopt_a_different_embedder(config_file, make_pdf, tmp_path):
    cfg = load_config(config_file)
    _seed(config_file, make_pdf, tmp_path, FakeEmbedder(model_id_value="a", dimension_value=8))

    # A different embedding model/dimension would normally mismatch — reindex resets.
    reindex(cfg, embedder=FakeEmbedder(model_id_value="b", dimension_value=16))

    # searchable under the new embedder (a mismatch would have raised instead)
    corpus = Corpus(cfg, embedder=FakeEmbedder(model_id_value="b", dimension_value=16))
    assert corpus.search("churn analysis for Q3")[0].document_name == "paper.pdf"


def test_reindex_empty_store_is_zero(config_file):
    assert reindex(load_config(config_file), embedder=FakeEmbedder()) == 0
