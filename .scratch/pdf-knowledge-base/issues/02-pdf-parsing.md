# 02 — PDF parsing: text extraction, page map, content hash, empty-text detection

Status: ready-for-agent
Depends on: 01
PRD: ../PRD.md  ·  ADRs: 0001

## Goal

Turn a born-digital PDF into extracted text with page provenance, plus the content
hash used for deduplication — the real (un-faked) front of the Ingest pipeline.

## Scope (in)

- Extract text from a PDF's text layer using pymupdf, preserving which page each
  span of text came from (a page map that later Chunking can carry through).
- Compute a stable content hash of the raw PDF bytes (for dedup in issue 04).
- Detect an empty / near-empty text layer and represent it as a clear failure
  result (not empty-but-successful) so nothing is silently indexed empty.
- Expose page count.

## Scope (out)

- OCR / scanned-PDF / Claude-vision fallback (out of scope for this PRD).
- Chunking and embedding (issue 05).

## Acceptance criteria

- A born-digital fixture PDF yields non-empty text with correct per-page
  attribution and correct page count. (Story 3, 10-foundation)
- An empty-text-layer fixture PDF produces the clear failure result. (Story 14)
- The content hash is stable across repeated reads of the same bytes and differs
  for different files. (Story 12-foundation)

## Testing

- Real pymupdf against tiny committed fixture PDFs (this component is not faked).
- Include at least one born-digital fixture and one empty-text-layer fixture.

## Comments

**Implemented.** `docvault.parsing`:

- `parse_pdf(path)` → `ParsedDocument(pages, content_hash)`; `PageText(number, text)`
  is 1-indexed; `full_text` / `page_count` derived. All frozen.
- `content_hash(bytes)` → sha256 hex (dedup foundation for issue 04).
- Empty/near-empty text layer → `EmptyTextError`; missing/unreadable/non-PDF →
  `ParseError` (both added to `docvault.errors`).
- Fixtures generated at test time via pymupdf (born-digital 2-page + empty-text),
  so no binaries committed.

Tests: 28 passing total (5 new). Covers page provenance, stable/distinct hashes,
empty-text failure, missing-file and non-PDF errors. pymupdf added as a dependency.
