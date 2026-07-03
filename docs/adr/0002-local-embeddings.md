# Embeddings run locally, not via an API

We only have an Anthropic API key, and **Anthropic offers no embeddings endpoint**
— so the key cannot produce the vectors that [ADR-0001](0001-vector-rag-not-directory-routing.md)
depends on. We chose a local open embedding model (sentence-transformers, e.g.
BAAI/bge or nomic-embed) over Voyage/OpenAI: no second API key, no per-token cost,
and document text never leaves the machine — the right default for a personal tool.

Consequence: the embedding model and its vector dimension are baked into the
stored index. Changing the embedding model requires re-embedding every Document
(cheap, since raw PDFs are retained). Claude (via the Anthropic key) is still used
for summarize, categorize, and the ask agent — just not for embeddings.
