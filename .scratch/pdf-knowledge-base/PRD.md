# PRD: Local CLI PDF Knowledge Base with Agentic RAG

Status: ready-for-agent

> Vocabulary follows `CONTEXT.md`. Architecture follows `docs/adr/0001`–`0003`.
> Capitalized terms (Document, Summary, Category, Structured directory, RAG,
> Chunk, Ingest) are glossary terms.

## Problem Statement

I accumulate PDFs (reports, papers, manuals, personal documents) and have no fast
way to (a) keep them organized or (b) get answers out of them later. Today,
finding "what did that document say about X" means remembering which file it was,
opening it, and skimming. I want to drop a PDF into a system once and later ask
questions in plain language and get an answer that tells me *which* document and
*where* in it the answer came from — so I can trust it and open the source.

## Solution

A local, CLI-driven knowledge base. I run one command to **Ingest** a PDF (or a
folder of them): the system parses it, writes a **Summary**, assigns a **Category**
from a fixed taxonomy, files the raw PDF into a **Structured directory** under that
Category, and indexes its text as embedded **Chunks** for **RAG**. Later I run an
`ask` command; a Claude agent (orchestrated by Strands) searches the Chunk index,
optionally narrows by Category or reads a whole Document, and answers — always
citing the source Document and page, with the file path so I can open it. Raw PDFs
are always kept, so the index can be rebuilt at any time. Everything runs locally;
only Claude calls leave the machine (embeddings are local — see ADR-0002).

## User Stories

### Ingest

1. As a user, I want to ingest a single PDF by path, so that it becomes searchable.
2. As a user, I want to ingest an entire folder of PDFs in one command, so that I can onboard a backlog at once.
3. As a user, I want each ingested PDF's text extracted from its text layer (born-digital), so that Chunks contain real content.
4. As a user, I want a concise Summary generated for each Document, so that I can browse what I have without opening files.
5. As a user, I want each Document assigned exactly one Category from a fixed taxonomy, so that the Structured directory stays predictable.
6. As a user, I want to define and edit the Category taxonomy in a config file, so that I control the organization scheme.
7. As a user, I want a Document that fits no Category to land in an `uncategorized` bucket, so that ingest never fails to file something.
8. As a user, I want the raw PDF copied into the Structured directory under its Category, so that the original is preserved and organized.
9. As a user, I want each Document's Summary and metadata (Category, source filename, page count, content hash, ingest time) persisted, so that I can list and audit my corpus.
10. As a user, I want the Document's text split into Chunks with the page number(s) each Chunk came from, so that answers can cite pages.
11. As a user, I want Chunks embedded with a local model and stored in a vector index, so that RAG works without an external embeddings API.
12. As a user, I want re-ingesting the same PDF (by content hash) to be skipped or explicitly re-indexed, so that I don't get duplicate entries.
13. As a user, I want ingest to report per-file outcome (ingested / skipped-duplicate / failed) when processing a folder, so that I know what happened.
14. As a user, I want a PDF whose text layer is empty to be reported as a clear failure (not silently indexed empty), so that I know it needs different handling.
15. As a user, I want ingest to continue past a single failing PDF in a batch, so that one bad file doesn't abort the whole run.

### Ask / RAG

16. As a user, I want to ask a one-off question from the CLI, so that I get an answer without a session.
17. As a user, I want an interactive chat mode, so that I can ask follow-up questions in context.
18. As a user, I want the agent to search the Chunk index for my question, so that answers are grounded in my Documents.
19. As a user, I want the agent to be able to search again with a refined query, so that hard questions aren't limited to one retrieval.
20. As a user, I want the agent to be able to narrow a search by Category, so that it can focus when I mention a kind of Document.
21. As a user, I want to list the available Categories, so that I know how my corpus is organized (and so the agent can too).
22. As a user, I want the agent to read a full Document when Chunks are insufficient, so that it can answer questions that need whole-document context.
23. As a user, I want every answer to cite the source Document(s) and page number(s), so that I can verify it.
24. As a user, I want the cited Document's file path printed, so that I can open the source.
25. As a user, I want a flag to auto-open the cited PDF (at the cited page where possible), so that verification is one step.
26. As a user, I want a clear "I couldn't find anything relevant" answer when retrieval is empty, so that the system doesn't fabricate.
27. As a user, I want answers to prefer my Documents over the model's own knowledge, so that the tool stays grounded in my corpus.

### Corpus management / config

28. As a user, I want to list all ingested Documents with their Category and Summary, so that I can see my library.
29. As a user, I want to configure which Claude model is used for Ingest vs Ask, so that I control the cost/quality trade-off (default: Haiku for Ingest, Sonnet for Ask).
30. As a user, I want configuration (categories, models, store location) to live in files I can edit, so that I don't need code changes for routine tweaks.
31. As a user, I want the storage location to be configurable, so that I can point it at a chosen directory.
32. As a user, I want to rebuild the vector index from the retained raw PDFs, so that I can recover from a corrupted index or change embedding models (per ADR-0002).

### Trust / operability

33. As a user, I want a missing Anthropic API key to produce a clear, actionable error, so that I know what to fix.
34. As a user, I want a helpful error when I point at a non-existent path or a non-PDF file, so that mistakes are obvious.
35. As a user, I want the tool to work fully offline for embedding and search (only Claude calls need network), so that my document text stays local except for the reasoning step.

## Implementation Decisions

- **Language / packaging.** Python. A **core library** holds all logic; a **thin CLI** adapter wraps it (per ADR seams and reuse — a future UI can call the same core). CLI verbs: `ingest`, `ask`, `chat`, `list`, `reindex` (exact names may adjust during build).
- **Agent framework.** Strands Agents is the orchestrator for the Ask path (ADR-0003). The agent is configured with three tools:
  - `search_documents(query, category?)` → top-k Chunks with Document + page provenance
  - `list_categories()` → the current taxonomy
  - `read_full_pdf(doc_id)` → full text of one Document
- **Ingest pipeline** (one Document at a time; per ADR-0001/0002):
  parse text + page map (pymupdf) → Summary (Claude) → Category (Claude, constrained to the fixed taxonomy) → file raw PDF into Structured directory under Category + persist metadata → Chunk (carrying page numbers) → embed (local model) → upsert into vector store.
- **Models.** Ingest (Summary + Category) uses `claude-haiku-4-5`; Ask agent uses `claude-sonnet-5`. Both configurable. Claude is reached via the official Anthropic SDK (Strands' Anthropic provider for the agent; a direct SDK call is acceptable for the Ingest summarize/categorize steps).
- **Categorization** is constrained: Claude must return one Category from the configured list, else `uncategorized`. New categories are NOT invented at ingest (fixed taxonomy decision).
- **Embeddings** are local (sentence-transformers, e.g. a `bge`/`nomic` small model) — no embeddings API (ADR-0002). The embedding model identity + vector dimension are recorded with the index so a mismatch on reindex is detectable.
- **Vector store.** ChromaDB, persistent, embedded (no server). Rebuildable from retained raw PDFs. (LanceDB is an acceptable substitute; not load-bearing.)
- **Storage layout.** Raw PDFs filed by Category (the Structured directory); Document metadata/Summaries persisted alongside; the vector index in its own store directory. All under one configurable root.
- **Provenance.** Each Chunk records the source Document id and originating page number(s). Citations are rendered as Document name + page(s) + file path; `--open` opens the PDF (at the page where the platform allows).
- **Deduplication.** Content hash per Document; re-ingest of an identical file is skipped by default, with an explicit re-index path.
- **External boundaries are injectable** to support the single test seam below: the LLM client and the embedder are passed into the core (dependency-injected), not hard-imported inside pipeline logic.

## Testing Decisions

- **What makes a good test here:** it drives the system through the **core library's public API** (`ingest`, `ask`) and asserts on **observable behavior** — a Document is filed under the expected Category, its Chunks are retrievable, an answer includes the expected content and a citation to the right Document/page — not on internal call sequences or private structures.
- **The single seam** (confirmed with the user): the core library API. Tests inject fakes only at the two external/non-deterministic boundaries — the **LLM client** (returns canned Summaries, Categories, and answers) and the **embedder** (returns deterministic vectors). Everything else runs for real: a real ephemeral/temp-dir ChromaDB, real pymupdf parsing against tiny committed fixture PDFs, real filesystem in a temp directory.
- **Modules tested through that seam:** the Ingest pipeline (parse→summarize→categorize→file→chunk→embed→index) and the Ask path (agent + the three tools + citation rendering), exercised end-to-end via `ingest`/`ask`.
- **CLI** is a thin adapter — smoke-tested only (argument parsing → core call → output shape), not re-testing core behavior.
- **Determinism:** the fake LLM makes summarize/categorize/answer deterministic; the fake embedder makes retrieval ordering deterministic; fixture PDFs make parsing deterministic. No network in the test suite.
- **Representative cases to cover:** single-file ingest files under the right Category and becomes searchable; folder ingest reports per-file outcomes and survives one bad file; duplicate re-ingest is skipped; empty-text PDF is a clear failure; `ask` returns an answer with a correct Document+page citation; `ask` with no relevant Chunks returns a "nothing relevant" answer rather than a fabrication; `list_categories`/category-narrowed search behave; `reindex` rebuilds from raw PDFs.
- **Prior art:** none yet (greenfield). This PRD's seam establishes the pattern subsequent tests should follow.

## Out of Scope

- Scanned / image-only PDFs and OCR / Claude-vision fallback (born-digital only for now — ADR notes the fallback exists as a future path).
- Web UI or any GUI (CLI first; core library is structured so a UI can reuse it later).
- Non-PDF formats (docx, html, images, etc.).
- Multi-user, auth, sharing, or a hosted/server deployment.
- Cloud vector stores or an embeddings API (local only — ADR-0002).
- Editing/annotating PDFs; the system reads and organizes, it does not modify source documents.
- Automatic taxonomy evolution (fixed taxonomy; propose-new was explicitly not chosen).
- Incremental/streaming ingest triggers (watched folders, upload endpoints) — ingest is explicit CLI commands.

## Further Notes

- **Repo name mismatch:** the repo is `agent-drawing`, which doesn't describe a PDF knowledge base. Package/module naming should reflect the actual domain (e.g. a `docvault`-style name); renaming the repo is optional and out of scope for this PRD.
- **No embeddings from the Anthropic key:** this is the single biggest gotcha and the reason for the local embedder (ADR-0002). Any future contributor tempted to "just use the API key for embeddings" should read that ADR first.
- **Why an agent for Q&A:** a fixed retrieve→answer pipeline would be simpler, but the agentic tools (multi-search, category narrowing, full-document read) are what let it answer harder questions and are what make Strands load-bearing (ADR-0003).
- **Suggested build order (from the grilling session):** (1) core skeleton — config, storage layout, data types; (2) Ingest pipeline, TDD per step through the seam; (3) retrieval + Strands Ask agent with the three tools + citations; (4) CLI verbs; (5) end-to-end verify on real PDFs.
