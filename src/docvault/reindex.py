"""Rebuild the vector index from the retained raw PDFs (ADR-0002).

Used for recovery (corrupt/lost index) or to adopt a new embedding model. Because
raw PDFs are always kept in the Structured directory, the index is fully
disposable. The rebuild is a Corpus operation; this is the thin entry point that
constructs a Corpus with the desired Embedder and rebuilds. Adopting a different
embedder is fine — the rebuild resets the recorded embedding metadata first, so no
EmbeddingMismatchError.
"""

from __future__ import annotations

from docvault.boundaries import Embedder
from docvault.config import Config
from docvault.corpus import Corpus


def reindex(config: Config, *, embedder: Embedder) -> int:
    """Rebuild the index from raw PDFs. Returns the number of Documents reindexed."""
    return Corpus(config, embedder=embedder).rebuild()
