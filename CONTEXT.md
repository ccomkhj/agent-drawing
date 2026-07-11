# Context / Glossary

The ubiquitous language for this project. Glossary only — no implementation details.

## Terms

### Document
A single ingested PDF. Has raw bytes (the original file, always kept), a summary,
and a category. One Document maps to one source PDF file.

### Summary
A short natural-language description of what a Document means, produced at ingest
time. Used both for human browsing and as retrieval/routing metadata.

### Category
The classification assigned to a Document at ingest time. Determines where the
Document's raw PDF and metadata are filed in the structured directory.

### Structured directory
The on-disk organization of ingested material, keyed by Category. Holds the raw
PDFs and their metadata/summaries. It is **organizational and for reference**, not
the primary retrieval mechanism — see [[RAG]].

### RAG (retrieval)
The question-answering path. Resolved to **vector RAG**: each Document is chunked,
chunks are embedded, and questions are answered by semantic similarity search over
the chunk vectors. Retrieved chunks are passed to Claude, which answers and cites
the source Document (and the system shows the reference PDF). The structured
directory is *not* the primary lookup — the vector index is.

### Chunk
A slice of a Document's text that is embedded and stored as a vector. The unit of
retrieval.

### Ingest
The pipeline that turns a raw PDF into stored, queryable material:
get PDF → parse → summarize → categorize → file into structured directory (+ keep
raw) → chunk + embed into the vector index.

### Corpus
The persisted body of ingested material behind a single interface: the retained
raw PDFs (the [[Structured directory]]) and the vector index of their [[Chunk]]s,
owned together. The store-and-index pair never appears in a caller — writing a
Document (raw first, then chunks) and searching it (semantic lookup joined back to
provenance) are Corpus operations. Its guarantees: a Document's raw PDF is written
before its chunks, so a partial write leaves a raw PDF the index rebuild can heal;
and search never returns a result it cannot fully attribute to a Document and
page(s).
