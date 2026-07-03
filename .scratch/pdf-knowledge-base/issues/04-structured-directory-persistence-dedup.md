# 04 — Structured directory filing, Document metadata persistence, deduplication

Status: ready-for-agent
Depends on: 01, 02, 03
PRD: ../PRD.md  ·  ADRs: 0001

## Goal

Persist an ingested Document: copy the raw PDF into the **Structured directory**
under its Category, write its metadata + Summary, and enforce dedup by content hash.

## Scope (in)

- File the raw PDF into the Structured directory keyed by Category (raw PDFs are
  always retained — enables rebuild per ADR-0002).
- Persist Document metadata: id, source filename, Category, Summary, page count,
  content hash, ingest time.
- Deduplicate by content hash: an identical file is skipped by default; expose an
  explicit re-index path (skip-vs-reindex signal for the orchestrator in issue 06).

## Scope (out)

- Chunking/embedding/indexing (issue 05); orchestration (issue 06).

## Acceptance criteria

- After filing, the raw PDF exists under `Structured directory/<Category>/` and its
  metadata + Summary are retrievable. (Stories 8, 9)
- Re-filing a Document with an already-seen content hash is reported as a duplicate
  and does not create a second entry. (Story 12)
- The Structured directory is organizational only — retrieval does not depend on it
  (ADR-0001).

## Testing

- Through the seam, in a temp-dir store (real filesystem). Assert placement path,
  metadata round-trip, and duplicate detection. No network.

## Comments

**Implemented.** `docvault.store`:

- `DocumentStore(config)` with `save` / `get` / `find_by_hash` / `list`, returning
  `StoredDocument(document, raw_path)`.
- Raw PDF filed under `raw/<category>/`; metadata+Summary persisted as JSON in
  `meta/<id>.json` (wraps `Document.to_dict()` + `raw_relpath`). Raw always retained.
- Dedup: `find_by_hash` for the orchestrator's skip check; `save` is idempotent per
  id (re-save overwrites, no second entry). Filename collisions between *different*
  Documents disambiguated with a short content-hash suffix.

Tests: 39 passing (6 new). Covers filing under Category, metadata round-trip,
find-by-hash (hit + miss), idempotent re-save, collision disambiguation, list, and
unknown-id → None. Real temp-dir filesystem, no network.
