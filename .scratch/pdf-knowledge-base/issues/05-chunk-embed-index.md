# 05 — Chunking with page provenance, local embedder, and vector index

Status: ready-for-agent
Depends on: 01, 02
PRD: ../PRD.md  ·  ADRs: 0001, 0002

## Goal

Turn a parsed Document into embedded **Chunks** stored in the vector index, with
each Chunk carrying the page number(s) it came from — the RAG substrate.

## Scope (in)

- Split Document text into Chunks, carrying source Document id and originating page
  number(s) through from the page map (issue 02).
- Embed Chunks with the local embedder (injected boundary; real impl is
  sentence-transformers, e.g. a `bge`/`nomic` small model — ADR-0002).
- Upsert Chunks + vectors + provenance metadata into ChromaDB (persistent,
  embedded; LanceDB acceptable substitute).
- Record the embedding-model identity and vector dimension with the index so a
  mismatch is detectable on reindex (issue 10).

## Scope (out)

- Query/search (issue 07); orchestration (issue 06).

## Acceptance criteria

- Chunks retain correct page provenance from the source Document. (Story 10)
- Chunks are embedded via the local embedder and stored/retrievable from the index.
  (Story 11)
- Embedding-model id + dimension are persisted alongside the index. (Story 32
  foundation)

## Testing

- Through the seam: inject the fake embedder (deterministic vectors); use a real
  ephemeral/temp-dir vector store. Assert Chunk count, page provenance preserved,
  and that stored vectors are retrievable by id. No network.

## Comments

**Implemented.**

- `docvault.chunking.chunk_document` — per-page overlapping windows; each Chunk
  keeps its single source page number; empty pages skipped.
- `docvault.index.VectorIndex` (ChromaDB persistent) — `add(chunks, embedder)`
  embeds + upserts, returns ids; `get`/`count`; embedding model+dimension persisted
  to `index/embedding.json`; `EmbeddingMismatchError` on incompatible embedder
  (added to errors) — reindex signal for issue 10.
- `docvault.embedding.LocalEmbedder` — real sentence-transformers impl (default
  `BAAI/bge-small-en-v1.5`), lazy-imported; added as the optional `embeddings`
  extra (`uv sync --extra embeddings`) so the default/test loop stays light.

Tests: 47 passing (8 new) — real temp-dir Chroma + fake embedder. Covers chunk
provenance/windowing, embed+store+read-back, multi-page provenance round-trip,
embedding metadata persistence, mismatch detection, empty-add no-op.
chromadb added as a dependency.
