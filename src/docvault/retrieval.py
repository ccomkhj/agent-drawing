"""Retrieval and the operations the Ask agent's tools expose.

Search embeds the question with the local embedder, queries the vector index, and
joins the store so each hit carries what a Citation needs (Document name + path).
The Strands tool wiring that calls these lives in issue 08.
"""

from __future__ import annotations

from dataclasses import dataclass

from docvault.boundaries import Embedder
from docvault.config import Config
from docvault.index import VectorIndex
from docvault.parsing import parse_pdf
from docvault.store import DocumentStore
from docvault.types import Citation


@dataclass(frozen=True, slots=True)
class SearchHit:
    """A retrieved Chunk with full provenance for building a Citation."""

    text: str
    document_id: str
    document_name: str
    pages: tuple[int, ...]
    path: str
    score: float

    def citation(self) -> Citation:
        return Citation(
            document_id=self.document_id,
            document_name=self.document_name,
            pages=self.pages,
            path=self.path,
        )


class Retriever:
    """The three retrieval operations the Ask agent uses as tools."""

    def __init__(self, config: Config, *, embedder: Embedder) -> None:
        self._config = config
        self._embedder = embedder
        self._store = DocumentStore(config)
        self._index = VectorIndex(config)

    def search(
        self, query: str, *, k: int = 5, category: str | None = None
    ) -> list[SearchHit]:
        """Semantic search over Chunks; optionally narrowed to a Category."""
        resolved = self._resolve_category(category)
        query_vector = self._embedder.embed([query])[0]
        hits = self._index.search(query_vector, k=k, category=resolved)
        return [h for h in (self._join(hit) for hit in hits) if h is not None]

    def list_categories(self) -> list[str]:
        """The configured Category taxonomy."""
        return list(self._config.categories)

    def read_full_pdf(self, document_id: str) -> str | None:
        """Full text of one Document (re-parsed from its retained raw PDF)."""
        stored = self._store.get(document_id)
        if stored is None:
            return None
        return parse_pdf(stored.raw_path).full_text

    # --- internals ------------------------------------------------------------

    def _resolve_category(self, category: str | None) -> str | None:
        if category is None:
            return None
        # Only filter by a Category that actually exists; otherwise search all.
        return category if category in self._config.categories else None

    def _join(self, hit) -> SearchHit | None:
        stored = self._store.get(hit.document_id)
        if stored is None:  # index/store drift — skip rather than crash
            return None
        return SearchHit(
            text=hit.text,
            document_id=hit.document_id,
            document_name=stored.document.source_filename,
            pages=hit.pages,
            path=str(stored.raw_path),
            score=hit.score,
        )
