"""Rebuild the vector index from the retained raw PDFs (ADR-0002).

Used for recovery (corrupt/lost index) or to adopt a new embedding model. Because
raw PDFs are always kept in the Structured directory, the index is fully
disposable — reset it and re-chunk + re-embed every Document. Adopting a different
embedder is fine: the reset clears the recorded embedding metadata first, so no
EmbeddingMismatchError.
"""

from __future__ import annotations

from docvault.boundaries import Embedder
from docvault.chunking import chunk_document
from docvault.config import Config
from docvault.index import VectorIndex
from docvault.parsing import parse_pdf
from docvault.store import DocumentStore


def reindex(config: Config, *, embedder: Embedder) -> int:
    """Rebuild the index from raw PDFs. Returns the number of Documents reindexed."""
    store = DocumentStore(config)
    index = VectorIndex(config)
    index.reset()

    count = 0
    for stored in store.list():
        parsed = parse_pdf(stored.raw_path)
        chunks = chunk_document(parsed, stored.document.id)
        index.add(chunks, embedder, category=stored.document.category)
        count += 1
    return count
