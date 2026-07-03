# Retrieval is vector RAG, not directory routing

The original ask described both a "structured directory format" and "RAG," which
imply different lookup mechanisms. We decided the **vector index is the primary
retrieval path**: each Document is chunked, embedded, and questions are answered
by semantic similarity search. The structured directory (raw PDFs filed by
Category) is kept for organization, browsing, and reference-back — not for lookup.
We chose this over Claude-reads-the-directory routing because it handles fuzzy,
cross-document questions on a growing corpus far better; the cost is running an
embedding + vector store (see [ADR-0002](0002-local-embeddings.md)). Raw PDFs are
always retained, so the index can be rebuilt at any time.
