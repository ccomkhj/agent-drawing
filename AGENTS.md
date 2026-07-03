# agent-drawing

A local, CLI-driven PDF knowledge base with agentic RAG over Claude. See
`CONTEXT.md` for the domain glossary and `docs/adr/` for architectural decisions.

## Agent skills

### Issue tracker

Issues and PRDs live as local markdown under `.scratch/<feature-slug>/` in this
repo. See `docs/agents/issue-tracker.md`.

### Triage labels

The five canonical triage roles, using their default strings unchanged. See
`docs/agents/triage-labels.md`.

### Domain docs

Single-context: one `CONTEXT.md` + `docs/adr/` at the repo root. See
`docs/agents/domain.md`.
