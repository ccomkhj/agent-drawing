# 08 — Strands Ask agent, grounded answers, and Citations

Status: ready-for-agent
Depends on: 07
PRD: ../PRD.md  ·  ADRs: 0003

## Goal

Assemble the `ask` entry point as a Strands agent (Sonnet by default) equipped with
the three tools, producing grounded answers that cite the source Document and page.

## Scope (in)

- `ask(question)` on the core library: a Strands agent configured with
  `search_documents`, `list_categories`, `read_full_pdf`, using the Ask model from
  config (`claude-sonnet-5` default) via the injected LLM client.
- The agent may search, re-search with a refined query, narrow by Category, or read
  a full Document when Chunks are insufficient.
- Answers prefer the corpus over model knowledge; when retrieval is empty, the
  answer is an explicit "couldn't find anything relevant," not a fabrication.
- Render Citations: Document name + page(s) + file path, attached to the answer.

## Scope (out)

- CLI, `chat` loop, `--open` (issue 09).

## Acceptance criteria

- A question answerable from an ingested fixture returns an answer whose content is
  grounded and carries a Citation to the correct Document + page. (Stories 16, 18,
  23, 24, 27)
- The agent can perform more than one retrieval and can narrow by Category when the
  question implies one. (Stories 19, 20)
- With no relevant Chunks, the answer states nothing relevant was found. (Story 26)

## Testing

- Through the seam: inject a fake LLM client that drives a deterministic tool
  sequence (e.g. call `search_documents`, then answer with the returned Chunk) and
  a fake embedder; real temp-dir index seeded via `ingest`. Assert answer content
  and Citation correctness (right Document, right page), and the empty-retrieval
  behavior. No network.

## Comments

**Implemented (seam option (a) — the Strands `Model` is the injected boundary).**
`docvault.agent`:

- `AskAgent(config, *, model, embedder)` builds a real `strands.Agent` with the
  three `@tool`s (search_documents / list_categories / read_full_pdf) closed over a
  `Retriever` + a citation collector; `answer(question) → Answer{text, citations}`.
- `anthropic_ask_model(config)` — production model via `strands.models.anthropic`
  (Ask model from config); exercised by the opt-in e2e (issue 10).
- Tests inject `ScriptedModel(Model)` (in fakes) which replays scripted turns
  (tool_turn / text_turn) as Strands StreamEvents, driving the **real** agent loop
  offline against the real tools + temp-dir index. Verified against the installed
  SDK's event shapes rather than guessed.

Tests: 64 passing (4 new). Grounded answer + correct top Citation (doc+page),
multi-search + category narrowing (both docs cited), empty retrieval → no
citations, read_full_pdf path.

**Known limitation (noted for a later refinement):** citations reflect *all*
retrieved hits (most-relevant first), not only the passages the model actually
used — with a tiny corpus and default `k`, low-relevance docs can appear. A score
threshold or model-attributed citations would tighten this.
