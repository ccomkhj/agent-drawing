# agent-drawing (`docvault`)

A local, CLI-driven **PDF knowledge base with agentic RAG** over Claude.

Drop PDFs in once — they're parsed, summarized, categorized, filed, and indexed.
Ask questions later in plain language and get an answer that **cites the source
document and page**, with the file path so you can open it.

Everything runs locally; only the Claude calls leave your machine (embeddings are
local — see [ADR-0002](docs/adr/0002-local-embeddings.md)).

## How it works

**Ingest** (`claude-haiku-4-5`)

```
PDF → text + page map (pymupdf) → Summary + Category (Claude, fixed taxonomy)
    → file raw PDF under store/raw/<category>/ + persist metadata
    → chunk (per page) → local embeddings → ChromaDB vector index
```

**Ask** — a [Strands](https://strandsagents.com/) agent (`claude-sonnet-5`) with tools

```
search_documents(query, category?) · list_categories() · read_full_pdf(doc_id)
→ Claude searches (maybe more than once), narrows by category, or reads a whole
  document → answers, grounded in your corpus, with [document, page] citations
```

Retrieval is **vector RAG** ([ADR-0001](docs/adr/0001-vector-rag-not-directory-routing.md)); the
structured directory is organization/reference only. The ask path is a genuine
tool-driven agent ([ADR-0003](docs/adr/0003-strands-agentic-rag.md)), not a fixed pipeline.

## Install

Requires Python ≥3.11 and [uv](https://docs.astral.sh/uv/).

```bash
uv sync --extra embeddings          # includes the local embedding model
export ANTHROPIC_API_KEY=sk-ant-... # Claude, for summarize/categorize/ask
```

> Anthropic has no embeddings API, so embeddings run locally via
> `sentence-transformers` (default `BAAI/bge-small-en-v1.5`). The first run
> downloads the model.

## Configure

Create a `docvault.yaml` (all fields optional — sensible defaults apply):

```yaml
store_root: ~/.docvault
models:
  ingest: claude-haiku-4-5
  ask: claude-sonnet-5
categories:      # fixed taxonomy; anything off-list → "uncategorized"
  - invoices
  - contracts
  - research
  - manuals
  - personal
```

## Usage

```bash
uv run docvault ingest ./papers/            # a file or a whole folder
uv run docvault ask "what did the Q3 report say about churn?"
uv run docvault ask "…" --open              # open the cited PDF
uv run docvault chat                        # interactive follow-ups
uv run docvault list                        # browse ingested documents
uv run docvault --config ./docvault.yaml ask "…"
```

Example answer:

```
Churn rose to 4.2% in Q3, driven by onboarding friction.

Sources:
  - q3-report.pdf p.4
    /Users/you/.docvault/raw/research/q3-report.pdf
```

Rebuild the index from the retained raw PDFs at any time (recovery, or an
embedding-model change): the index is disposable because raw PDFs are always kept.

## Develop

```bash
uv run pytest            # 77 offline tests (no network, no API key)
```

Tests drive behavior through **one seam** — the core library API — faking only the
two external, non-deterministic boundaries (the **LLM client** and the
**embedder**) while running real ChromaDB, real pymupdf, and the real Strands agent
loop against fixtures. The opt-in end-to-end check (`tests/test_e2e.py`) hits the
real Claude API + local embedder and is skipped unless `ANTHROPIC_API_KEY` is set
and the `embeddings` extra is installed.

## Project layout

```
src/docvault/      core library (config, parsing, ingest, retrieval, agent, cli, …)
tests/             pytest suite + fakes
CONTEXT.md         domain glossary
docs/adr/          architectural decision records
.scratch/          PRD + implementation issues
```

## Known limitations

- Born-digital PDFs only (no OCR / scanned-document fallback yet).
- Citations reflect all retrieved passages (most-relevant first), not only the
  ones the model ultimately used.
