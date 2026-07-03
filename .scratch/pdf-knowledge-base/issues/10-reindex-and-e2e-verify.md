# 10 — Reindex from raw PDFs and end-to-end verification

Status: ready-for-agent
Depends on: 05, 06, 09
PRD: ../PRD.md  ·  ADRs: 0002

## Goal

Make the vector index rebuildable from the retained raw PDFs, and verify the whole
system end-to-end on real PDFs with a real Claude call.

## Scope (in)

- `reindex`: rebuild the vector index from the raw PDFs in the Structured directory
  (re-chunk + re-embed), for recovery or an embedding-model change (ADR-0002).
- Detect an embedding-model / dimension mismatch against the stored index metadata
  (issue 05) and handle it explicitly (rebuild rather than corrupt).
- End-to-end verification: ingest a couple of real fixture PDFs and run `ask`
  against the **real** Anthropic API + real local embedder, confirming a grounded
  answer with a correct Citation.

## Scope (out)

- OCR, non-PDF formats, web UI (all out of scope for the PRD).

## Acceptance criteria

- `reindex` reconstructs a working index from raw PDFs alone (index deletable and
  recoverable). (Story 32)
- An embedding-model/dimension mismatch is detected and triggers a rebuild rather
  than silent breakage. (Story 32)
- Manual/opt-in e2e run: real ingest + real `ask` yields a grounded answer with a
  correct Document + page Citation on a real PDF. (End-to-end trust; verifies the
  whole PRD)

## Testing

- `reindex` logic tested through the seam (fake embedder, temp-dir store): delete
  index, reindex from raw PDFs, assert Chunks restored with provenance; assert
  mismatch detection.
- The real-API end-to-end check is an opt-in test/script (guarded by presence of an
  Anthropic key), kept out of the default no-network suite.

## Comments

**Implemented.** `docvault.reindex.reindex(config, *, embedder)` + `VectorIndex.reset()`:

- `reset()` drops the collection and the recorded embedding metadata; `reindex`
  resets then re-parses every retained raw PDF → re-chunk → re-embed → re-add,
  returning the count. Because reset clears the embedding metadata, a rebuild can
  adopt a **different** embedder (model/dimension) without EmbeddingMismatchError.
- `tests/test_e2e.py` — opt-in real-API + real-LocalEmbedder check, skipped unless
  `ANTHROPIC_API_KEY` is set AND the `embeddings` extra is installed. Real ingest
  (Haiku) + real Strands/Claude ask → grounded answer with a q3.pdf Citation.

Tests: 77 passing + 1 skipped (e2e). Reindex covers rebuild-after-loss (provenance
restored + searchable), adopting a different embedder, and empty store → 0.
