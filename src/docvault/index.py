"""The vector index — the primary retrieval mechanism (ADR-0001).

Chunks are embedded with the injected local Embedder (ADR-0002) and stored in a
persistent ChromaDB collection. The embedder's model id and vector dimension are
recorded alongside the index so a mismatch is detectable on reindex.

Search lives in issue 07; this module handles chunking's downstream — embed +
upsert + read-back + embedding metadata.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import chromadb

from docvault.boundaries import Embedder
from docvault.config import Config
from docvault.errors import EmbeddingMismatchError
from docvault.types import Chunk

_COLLECTION = "chunks"
_EMBEDDING_META = "embedding.json"


@dataclass(frozen=True, slots=True)
class IndexedChunk:
    """A Chunk as stored in the index, with its id and embedding."""

    id: str
    text: str
    document_id: str
    pages: tuple[int, ...]
    embedding: list[float]
    category: str | None = None


@dataclass(frozen=True, slots=True)
class IndexHit:
    """A search result at the chunk level (join to the store for name/path)."""

    chunk_id: str
    text: str
    document_id: str
    pages: tuple[int, ...]
    category: str | None
    score: float


class VectorIndex:
    """Persistent ChromaDB-backed index of embedded Chunks."""

    def __init__(self, config: Config) -> None:
        self._dir = config.index_dir
        self._dir.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=str(self._dir))
        self._collection = self._client.get_or_create_collection(
            name=_COLLECTION, metadata={"hnsw:space": "cosine"}
        )

    # --- writes ---------------------------------------------------------------

    def add(
        self,
        chunks: list[Chunk],
        embedder: Embedder,
        *,
        category: str | None = None,
    ) -> list[str]:
        """Embed and upsert Chunks; returns the assigned chunk ids.

        ``category`` (the source Document's Category) is stored on each chunk so
        searches can be narrowed by Category. Raises EmbeddingMismatchError if a
        prior index used a different embedder.
        """
        if not chunks:
            return []
        self._ensure_embedding_compatible(embedder)

        ids = [self._chunk_id(c, i) for i, c in enumerate(chunks)]
        texts = [c.text for c in chunks]
        embeddings = embedder.embed(texts)
        metadatas = [self._metadata(c, category) for c in chunks]
        self._collection.upsert(
            ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas
        )
        return ids

    def search(
        self, query_embedding: list[float], *, k: int = 5, category: str | None = None
    ) -> list[IndexHit]:
        """Return the k nearest chunks, optionally restricted to a Category."""
        if self.count() == 0:
            return []
        where = {"category": category} if category else None
        result = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        hits: list[IndexHit] = []
        for cid, text, meta, dist in zip(
            result["ids"][0],
            result["documents"][0],
            result["metadatas"][0],
            result["distances"][0],
        ):
            hits.append(
                IndexHit(
                    chunk_id=cid,
                    text=text,
                    document_id=meta["document_id"],
                    pages=tuple(json.loads(meta["pages"])),
                    category=meta.get("category"),
                    score=1.0 - float(dist),  # cosine distance → similarity
                )
            )
        return hits

    # --- reads ----------------------------------------------------------------

    def count(self) -> int:
        return self._collection.count()

    def get(self, chunk_id: str) -> IndexedChunk | None:
        result = self._collection.get(
            ids=[chunk_id], include=["documents", "metadatas", "embeddings"]
        )
        if not result["ids"]:
            return None
        meta = result["metadatas"][0]
        return IndexedChunk(
            id=result["ids"][0],
            text=result["documents"][0],
            document_id=meta["document_id"],
            pages=tuple(json.loads(meta["pages"])),
            embedding=list(result["embeddings"][0]),
            category=meta.get("category"),
        )

    def embedding_metadata(self) -> dict | None:
        path = self._dir / _EMBEDDING_META
        if not path.exists():
            return None
        return json.loads(path.read_text())

    def reset(self) -> None:
        """Drop all chunks and the recorded embedding metadata (for reindex).

        Clearing the metadata lets a rebuild adopt a different embedder without an
        EmbeddingMismatchError.
        """
        try:
            self._client.delete_collection(_COLLECTION)
        except Exception:  # collection may not exist yet
            pass
        self._collection = self._client.get_or_create_collection(
            name=_COLLECTION, metadata={"hnsw:space": "cosine"}
        )
        meta = self._dir / _EMBEDDING_META
        if meta.exists():
            meta.unlink()

    # --- internals ------------------------------------------------------------

    def _chunk_id(self, chunk: Chunk, seq: int) -> str:
        return f"{chunk.document_id}-{seq:04d}"

    def _metadata(self, chunk: Chunk, category: str | None) -> dict:
        meta = {"document_id": chunk.document_id, "pages": json.dumps(list(chunk.pages))}
        if category is not None:
            meta["category"] = category
        return meta

    def _ensure_embedding_compatible(self, embedder: Embedder) -> None:
        path = self._dir / _EMBEDDING_META
        current = {"model_id": embedder.model_id, "dimension": embedder.dimension}
        existing = self.embedding_metadata()
        if existing is None:
            path.write_text(json.dumps(current, indent=2))
            return
        if existing != current:
            raise EmbeddingMismatchError(
                f"Index built with {existing}, but embedder is {current}. "
                f"Reindex from raw PDFs to rebuild."
            )
