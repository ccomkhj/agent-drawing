"""Ingest orchestration — the top-of-seam entry point.

Wires the pipeline for one PDF or a whole folder:
parse -> summarize -> categorize -> file + persist -> chunk -> embed -> index.
A folder reports a per-file outcome and continues past a failing file. Duplicates
(by content hash) are skipped before the expensive LLM steps.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from docvault.boundaries import Embedder, LLMClient
from docvault.chunking import chunk_document
from docvault.config import Config
from docvault.enrichment import categorize, summarize
from docvault.errors import DocVaultError
from docvault.index import VectorIndex
from docvault.parsing import parse_pdf
from docvault.store import DocumentStore
from docvault.types import Document, utc_now

INGESTED = "ingested"
SKIPPED_DUPLICATE = "skipped_duplicate"
FAILED = "failed"

#: content-hash prefix length used as the Document id (identical content -> same id)
_ID_LEN = 16


@dataclass(frozen=True, slots=True)
class IngestOutcome:
    """The result of attempting to ingest one PDF."""

    path: Path
    status: str
    document: Document | None = None
    error: str | None = None


class Ingestor:
    """Runs the ingest pipeline with injected LLM + Embedder (the seam)."""

    def __init__(self, config: Config, *, llm: LLMClient, embedder: Embedder) -> None:
        self._config = config
        self._llm = llm
        self._embedder = embedder
        self._store = DocumentStore(config)
        self._index = VectorIndex(config)

    def ingest(self, path: str | Path, *, force: bool = False) -> list[IngestOutcome]:
        """Ingest a single PDF or every PDF under a folder.

        ``force`` re-ingests a Document even if its content hash is already known.
        """
        path = Path(path)
        targets = self._collect(path)
        return [self._ingest_one(p, force=force) for p in targets]

    # --- internals ------------------------------------------------------------

    def _collect(self, path: Path) -> list[Path]:
        if path.is_dir():
            return sorted(path.rglob("*.pdf"))
        return [path]

    def _ingest_one(self, path: Path, *, force: bool) -> IngestOutcome:
        try:
            parsed = parse_pdf(path)

            if not force:
                existing = self._store.find_by_hash(parsed.content_hash)
                if existing is not None:
                    return IngestOutcome(
                        path=path,
                        status=SKIPPED_DUPLICATE,
                        document=existing.document,
                    )

            summary = summarize(
                parsed.full_text, llm=self._llm, model=self._config.ingest_model
            )
            category = categorize(parsed.full_text, llm=self._llm, config=self._config)
            document = Document(
                id=parsed.content_hash[:_ID_LEN],
                source_filename=path.name,
                category=category,
                summary=summary,
                page_count=parsed.page_count,
                content_hash=parsed.content_hash,
                ingested_at=utc_now(),
            )
            self._store.save(document, path.read_bytes())
            self._index.add(
                chunk_document(parsed, document.id),
                self._embedder,
                category=document.category,
            )
            return IngestOutcome(path=path, status=INGESTED, document=document)

        except DocVaultError as exc:
            return IngestOutcome(path=path, status=FAILED, error=str(exc))
        except Exception as exc:  # keep a batch alive past an unexpected failure
            return IngestOutcome(path=path, status=FAILED, error=repr(exc))
