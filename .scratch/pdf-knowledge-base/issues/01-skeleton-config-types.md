# 01 — Project skeleton, configuration, domain types, and injectable boundaries

Status: ready-for-agent
Depends on: —
PRD: ../PRD.md  ·  ADRs: 0001, 0002, 0003

## Goal

Stand up the Python project and the foundations everything else builds on: the
core-library / thin-CLI split, editable configuration, the domain data types, and
the two injectable external boundaries that make the single test seam possible.

## Scope (in)

- Python packaging (pyproject, a `core` library package + a `cli` entry point that
  is a thin wrapper). Package/module naming should reflect the domain (a
  `docvault`-style name), not the repo name — see PRD Further Notes.
- Configuration loaded from editable files under one configurable root:
  - the Category taxonomy (a fixed list; supports an `uncategorized` fallback)
  - the two Claude models (default: `claude-haiku-4-5` for Ingest,
    `claude-sonnet-5` for Ask)
  - the storage root / store locations
- Domain data types from the glossary: **Document** (id, source filename,
  Category, Summary, page count, content hash, ingest time), **Chunk** (text,
  source Document id, page number(s)), **Citation** (Document, page(s), path).
- Two dependency-injected boundary interfaces (protocols): an **LLM client** and an
  **Embedder**. Core logic depends on these, never on a hard import of the SDK or
  embedding lib (this is the seam — PRD Testing Decisions).
- Test doubles: a fake LLM client and a fake embedder for the test suite to inject.

## Scope (out)

- Any pipeline logic (parsing, summarizing, indexing) — later issues.

## Acceptance criteria

- Config parses from the editable files; taxonomy, models, and store root are
  readable via the core API. (Stories 6, 29, 30, 31)
- A missing Anthropic API key surfaces a clear, actionable error path (the concrete
  raising happens where Claude is called, but the config/boundary shape must make
  it a clean single failure point). (Story 33)
- Domain types round-trip (construct → persist shape → reconstruct) for Document
  metadata. (Story 9, foundation)
- Fake LLM/embedder doubles exist and are usable by tests.

## Testing

- Unit-test config loading and taxonomy parsing (valid list, malformed file,
  `uncategorized` fallback presence).
- Establish the seam: confirm core entry points accept an injected LLM client and
  embedder. No network in tests.

## Comments

**Implemented.** uv project (src layout), Python ≥3.11.

- `docvault.config` — `Config` (frozen) + `load_config`; editable YAML, defaults for
  omitted fields, `ConfigError` on missing/malformed/invalid; `resolve_category`
  (fixed-taxonomy fallback to `uncategorized`); derived `raw_dir`/`index_dir`/`meta_dir`.
- `docvault.types` — frozen `Document` (with `to_dict`/`from_dict` round-trip),
  `Chunk` (page provenance), `Citation`; `utc_now` clock.
- `docvault.boundaries` — `LLMClient` + `Embedder` runtime-checkable Protocols (the seam).
- `docvault.auth` — `require_api_key()` single failure point → `MissingApiKeyError`.
- `docvault.cli` — thin `main` stub (verbs deferred to issue 09).
- `tests/fakes.py` — `FakeLLMClient` / `FakeEmbedder` doubles for the suite.

Tests: 23 passing, offline. Covers config load/defaults/errors, taxonomy fallback,
Document round-trip + immutability, missing-key error, seam protocol conformance.
CLI console script + package imports smoke-tested.
