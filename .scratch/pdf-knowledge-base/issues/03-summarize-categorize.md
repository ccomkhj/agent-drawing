# 03 — Ingest LLM steps: Summary generation and Category assignment

Status: ready-for-agent
Depends on: 01, 02
PRD: ../PRD.md  ·  ADRs: 0001, 0003

## Goal

Given a parsed Document's text, produce its **Summary** and assign one **Category**
from the fixed taxonomy, using the injected LLM client (Haiku by default).

## Scope (in)

- Summarize a Document into a concise natural-language Summary.
- Categorize the Document by asking Claude to choose exactly one Category from the
  configured taxonomy; anything not matching falls back to `uncategorized`.
- Use the Ingest model from config (`claude-haiku-4-5` default) via the injected
  LLM client — no hard SDK import in core logic.

## Scope (out)

- Filing/persistence (issue 04); chunking/embedding (issue 05).
- Inventing new Categories at ingest (fixed taxonomy — explicitly not chosen).

## Acceptance criteria

- Summarize returns a non-empty Summary for a Document. (Story 4)
- Categorize returns exactly one Category drawn from the configured list. (Story 5)
- A Document Claude can't place maps to `uncategorized`, never a fabricated label.
  (Story 5, 7)

## Testing

- Through the seam: inject the fake LLM client returning canned summaries and
  category choices. Assert Summary is captured and the chosen Category is
  constrained to the taxonomy (including the `uncategorized` fallback when the fake
  returns an off-list value). Deterministic; no network.

## Comments

**Implemented.** `docvault.enrichment`:

- `summarize(text, *, llm, model)` → concise Summary via injected LLM.
- `categorize(text, *, llm, config)` → uses `config.ingest_model`; prompt lists the
  taxonomy; `_match_category` normalizes case/quotes/trailing-period and matches the
  fixed list case-insensitively, else `UNCATEGORIZED`. Never invents a category.

Tests: 33 passing (5 new). Covers summary passthrough on the ingest model, exact
category match, case/punctuation normalization, off-list fallback, and that the
prompt communicates the taxonomy.
