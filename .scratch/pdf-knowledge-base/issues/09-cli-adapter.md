# 09 — CLI adapter: verbs, --open, list, and error handling

Status: ready-for-agent
Depends on: 06, 08
PRD: ../PRD.md  ·  ADRs: —

## Goal

Expose the core library through a thin CLI: the everyday commands, source-opening,
corpus listing, and friendly errors. The CLI holds no business logic.

## Scope (in)

- Verbs: `ingest <file|folder>`, `ask "<question>"`, `chat` (interactive
  follow-ups), `list` (Documents with Category + Summary).
- `--open` on `ask`/`chat`: open the cited PDF (at the cited page where the platform
  allows).
- Friendly, actionable errors: missing Anthropic API key; non-existent path;
  non-PDF file.
- Print answers with their Citations and file paths.

## Scope (out)

- `reindex` (issue 10). Any GUI/web (out of scope for the PRD).

## Acceptance criteria

- `ingest`, `ask`, `chat`, `list` invoke the core and render results/outcomes.
  (Stories 1, 2, 16, 17, 28)
- `--open` opens the cited PDF. (Story 25)
- Missing key / bad path / non-PDF produce clear errors. (Stories 33, 34)
- `chat` supports follow-up questions in context. (Story 17)

## Testing

- CLI is a thin adapter: smoke-test argument parsing → core call → output shape
  (inject fakes into the core as elsewhere). Do not re-test core behavior here.

## Comments

**Implemented.** `docvault.cli` (thin) + `docvault.anthropic_client`:

- Verbs via argparse: `ingest <path> [--force]`, `ask <q> [--open]`, `chat`, `list`
  (+ global `--config`). `main`/`_dispatch`/`_chat` build real deps (LocalEmbedder,
  AnthropicLLMClient, anthropic_ask_model) and are thin wiring (no-cover).
- Command handlers `cmd_ingest` / `cmd_ask` / `cmd_list` take injected deps and are
  smoke-tested with fakes; pure formatters `format_ingest` / `format_answer`
  (answer + Sources with doc p.N + path) / `format_list`. `--open` calls an
  injectable opener (`open_pdf` default). `validate_ingest_path` → clear errors for
  missing path / non-PDF.
- `AnthropicLLMClient` implements the `LLMClient` boundary via the Anthropic SDK;
  fails fast with `MissingApiKeyError` before importing the SDK (production; e2e in
  issue 10).

Tests: 74 passing (10 new). Covers all three formatters, ingest→list wiring,
ask rendering + PDF-open, and the missing-path / non-PDF / missing-key errors.
