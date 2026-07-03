# 07 — Retrieval and the three agent tools

Status: ready-for-agent
Depends on: 05, 06
PRD: ../PRD.md  ·  ADRs: 0001, 0003

## Goal

Provide the retrieval layer and expose it as the three tools the Ask agent will
use, with correct provenance flowing into Citations.

## Scope (in)

- `search_documents(query, category?)`: embed the query (local embedder), return
  top-k Chunks with their Document + page provenance; support narrowing by Category.
- `list_categories()`: return the current taxonomy.
- `read_full_pdf(doc_id)`: return the full text of one Document.
- Shape results so downstream can render a Citation (Document + page(s) + path).

## Scope (out)

- The agent loop / answer generation (issue 08).

## Acceptance criteria

- `search_documents` returns relevant Chunks with correct Document + page
  provenance; the `category` filter restricts results to that Category.
  (Stories 18, 20, 23)
- `list_categories` reflects the configured taxonomy. (Story 21)
- `read_full_pdf` returns the full Document text for a valid id. (Story 22)
- Empty/irrelevant retrieval returns an empty result the agent can act on (no
  fabricated Chunks). (Story 26 foundation)

## Testing

- Through the seam: fake embedder (deterministic vectors so ordering is
  predictable) + real temp-dir index seeded via `ingest`. Assert retrieved Chunk
  provenance, the Category filter, `list_categories`, and `read_full_pdf`.

## Comments

**Implemented.** `docvault.retrieval.Retriever(config, *, embedder)`:

- `search(query, k, category?)` — embeds the query, queries the index, joins the
  store so each `SearchHit` carries `document_name` + `path`; `.citation()` builds a
  `Citation`. Chunks now store `category` in index metadata (`VectorIndex.add(...,
  category=...)`, added `IndexHit` + `VectorIndex.search`); ingest passes the
  Document's Category through. Category filter falls back to all if the label is
  unknown; empty index → `[]`.
- `list_categories()` → configured taxonomy.
- `read_full_pdf(document_id)` — re-parses the retained raw PDF; unknown id → None.

Tests: 60 passing (7 new). Querying with a chunk's own text makes it the
deterministic top hit (provenance, name, path asserted); Category narrowing;
citation build; empty-index; list_categories; read_full_pdf hit + miss.
