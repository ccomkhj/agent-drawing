"""Behavior of the vector index, using a real temp-dir Chroma + fake embedder."""

from __future__ import annotations

from pathlib import Path

import pytest

from docvault.config import load_config
from docvault.errors import EmbeddingMismatchError
from docvault.index import VectorIndex
from docvault.types import Chunk
from tests.fakes import FakeEmbedder


def _chunks() -> list[Chunk]:
    return [
        Chunk(text="churn rose 4 percent", document_id="doc-1", pages=(4,)),
        Chunk(text="revenue grew", document_id="doc-1", pages=(5, 6)),
    ]


def test_add_embeds_and_stores_chunks(config_file: Path):
    index = VectorIndex(load_config(config_file))
    embedder = FakeEmbedder(dimension_value=8)

    ids = index.add(_chunks(), embedder)

    assert index.count() == 2
    stored = index.get(ids[0])
    assert stored is not None
    assert stored.text == "churn rose 4 percent"
    assert stored.document_id == "doc-1"
    assert stored.pages == (4,)
    assert len(stored.embedding) == 8


def test_page_provenance_round_trips_including_multi_page(config_file: Path):
    index = VectorIndex(load_config(config_file))
    ids = index.add(_chunks(), FakeEmbedder())

    assert index.get(ids[1]).pages == (5, 6)


def test_embedding_metadata_is_persisted(config_file: Path):
    index = VectorIndex(load_config(config_file))
    index.add(_chunks(), FakeEmbedder(model_id_value="fake-x", dimension_value=8))

    meta = index.embedding_metadata()
    assert meta == {"model_id": "fake-x", "dimension": 8}


def test_embedder_mismatch_is_detected(config_file: Path):
    cfg = load_config(config_file)
    VectorIndex(cfg).add(_chunks(), FakeEmbedder(model_id_value="a", dimension_value=8))

    # A new index over the same dir with a different embedder must refuse.
    with pytest.raises(EmbeddingMismatchError):
        VectorIndex(cfg).add(_chunks(), FakeEmbedder(model_id_value="b", dimension_value=8))


def test_adding_nothing_is_a_noop(config_file: Path):
    index = VectorIndex(load_config(config_file))

    assert index.add([], FakeEmbedder()) == []
    assert index.count() == 0
