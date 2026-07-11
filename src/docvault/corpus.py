"""The Corpus: the persisted body of ingested material behind one interface.

The retained raw PDFs (the Structured directory) and the vector index of their
Chunks are owned together (CONTEXT.md). Callers never touch the store and index as
a pair — writing a Document, searching it, reading it back, and rebuilding the
index are all Corpus operations. The DocumentStore and VectorIndex live behind this
seam as internal collaborators; the injected Embedder (ADR-0002) stays the only
external boundary for the vector side.

Guarantees (the contract):
- ``add`` writes the raw PDF *before* its chunks. A crash between the two leaves a
  retained raw PDF with no chunks — which ``rebuild`` heals. There is no two-phase
  commit across the filesystem and Chroma; store-first ordering plus the disposable
  index (ADR-0002) is the guarantee instead.
- ``search`` never returns a hit it cannot fully attribute to a Document and
  page(s): a chunk whose Document is missing from the store (drift) is skipped
  rather than returned or raised.
"""

from __future__ import annotations

from dataclasses import dataclass

from docvault.boundaries import Embedder
from docvault.chunking import chunk_document
from docvault.config import Config
from docvault.errors import DocVaultError
from docvault.index import VectorIndex
from docvault.parsing import ParsedDocument, parse_pdf
from docvault.store import DocumentStore, StoredDocument
from docvault.types import Citation, Document


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


class Corpus:
    """Raw PDFs + their vector index, owned together behind one interface."""

    def __init__(self, config: Config, *, embedder: Embedder | None = None) -> None:
        self._config = config
        self._embedder = embedder
        self._store = DocumentStore(config)
        self._index = VectorIndex(config)

    def _require_embedder(self) -> Embedder:
        """The Embedder is needed only by operations that embed (add, search,
        rebuild); read-only listing/reading works without one, so a Corpus built
        for those (e.g. ``docvault list``) need not load an embedding model."""
        if self._embedder is None:
            raise DocVaultError("This operation needs an embedder, but none was provided.")
        return self._embedder

    # --- writes ---------------------------------------------------------------

    def add(
        self, document: Document, pdf_bytes: bytes, parsed: ParsedDocument
    ) -> StoredDocument:
        """File the raw PDF and index its chunks — raw first (the contract).

        Chunking and embedding happen behind the seam; callers pass the parsed
        Document, never Chunks or vectors.
        """
        embedder = self._require_embedder()
        stored = self._store.save(document, pdf_bytes)
        self._index.add(
            chunk_document(parsed, document.id),
            embedder,
            category=document.category,
        )
        return stored

    def rebuild(self) -> int:
        """Rebuild the index from the retained raw PDFs. Returns the count rebuilt.

        Index-only: raw storage is the source of truth and is never re-written.
        The reset clears the recorded embedding metadata first, so a Corpus built
        with a different Embedder adopts it without an EmbeddingMismatchError.
        """
        embedder = self._require_embedder()
        self._index.reset()
        count = 0
        for stored in self._store.list():
            parsed = parse_pdf(stored.raw_path)
            self._index.add(
                chunk_document(parsed, stored.document.id),
                embedder,
                category=stored.document.category,
            )
            count += 1
        return count

    # --- reads ----------------------------------------------------------------

    def search(
        self, query: str, *, k: int = 5, category: str | None = None
    ) -> list[SearchHit]:
        """Semantic search over Chunks; optionally narrowed to a Category.

        The query is embedded internally. Hits are joined back to the store for
        provenance; a hit whose Document is missing (drift) is skipped.
        """
        resolved = self._resolve_category(category)
        query_vector = self._require_embedder().embed([query])[0]
        hits = self._index.search(query_vector, k=k, category=resolved)
        return [h for h in (self._join(hit) for hit in hits) if h is not None]

    def read_full(self, document_id: str) -> str | None:
        """Full text of one Document (re-parsed from its retained raw PDF)."""
        stored = self._store.get(document_id)
        if stored is None:
            return None
        return parse_pdf(stored.raw_path).full_text

    def documents(self) -> list[StoredDocument]:
        """Every stored Document (for listing and dedup)."""
        return self._store.list()

    def find_by_hash(self, content_hash: str) -> StoredDocument | None:
        """An existing Document with this content hash, if any (deduplication)."""
        return self._store.find_by_hash(content_hash)

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
