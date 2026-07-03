# 06 — Ingest orchestration and the `ingest` core behavior

Status: ready-for-agent
Depends on: 02, 03, 04, 05
PRD: ../PRD.md  ·  ADRs: 0001

## Goal

Wire the pipeline stages into the top-of-seam `ingest` entry point: parse →
summarize → categorize → file + persist → chunk → embed → index, for a single file
or a whole folder, with robust batch behavior.

## Scope (in)

- `ingest(path)` on the core library: accepts a single PDF path or a folder.
- Folder ingest processes each PDF and reports a per-file outcome:
  ingested / skipped-duplicate / failed.
- A single failing PDF (e.g. empty text layer, unreadable file) does not abort the
  batch — the run continues and the failure is reported.
- Skip duplicates by content hash (from issue 04) by default.

## Scope (out)

- Ask/retrieval (issues 07–08); CLI adapter (issue 09).

## Acceptance criteria

- Ingesting a single born-digital fixture files it under the expected Category and
  makes its Chunks searchable in the index. (Stories 1, 5, 8, 11)
- Folder ingest returns per-file outcomes and continues past a bad file.
  (Stories 2, 13, 15)
- Re-ingesting an identical file is reported as skipped-duplicate. (Story 12)
- An empty-text PDF is reported as a clear failure, not indexed empty. (Story 14)

## Testing

- This is the primary seam entry point. Inject fake LLM + fake embedder; real
  temp-dir Chroma + real pymupdf on fixtures. Assert observable outcomes (filed
  Category, index contents, per-file outcome list), not internal call order.

## Comments

**Implemented.** `docvault.ingest`:

- `Ingestor(config, *, llm, embedder)` — the seam entry point; builds store + index.
- `ingest(path, *, force=False)` — single PDF or recursive folder; returns
  `IngestOutcome(path, status, document, error)` per file with statuses
  `ingested` / `skipped_duplicate` / `failed`.
- Pipeline: parse → dedup-check (skip **before** LLM) → summarize → categorize →
  file+persist → chunk → embed+index. Document id = content-hash prefix (stable →
  natural dedup + idempotent). Batch survives a failing file (both `DocVaultError`
  and unexpected exceptions become `failed` outcomes).

Tests: 53 passing (6 new). Covers single-file file-under-category + index populated,
folder per-file outcomes surviving a bad file, duplicate skip (no second entry),
empty-text clear failure (nothing indexed), off-list category → uncategorized, and
`force` re-ingest. Added a `make_pdf` factory fixture.
