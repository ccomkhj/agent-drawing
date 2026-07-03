"""Domain data types (glossary terms from CONTEXT.md).

All types are immutable (frozen dataclasses) per the project coding style: never
mutate an existing instance, construct a new one.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True, slots=True)
class Document:
    """A single ingested PDF: raw bytes are kept on disk; this is its metadata.

    One Document maps to one source PDF file.
    """

    id: str
    source_filename: str
    category: str
    summary: str
    page_count: int
    content_hash: str
    ingested_at: datetime

    def to_dict(self) -> dict:
        """JSON-serializable form for persistence (ingested_at as ISO-8601)."""
        return {
            "id": self.id,
            "source_filename": self.source_filename,
            "category": self.category,
            "summary": self.summary,
            "page_count": self.page_count,
            "content_hash": self.content_hash,
            "ingested_at": self.ingested_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> Document:
        """Reconstruct from the form produced by to_dict()."""
        return cls(
            id=data["id"],
            source_filename=data["source_filename"],
            category=data["category"],
            summary=data["summary"],
            page_count=int(data["page_count"]),
            content_hash=data["content_hash"],
            ingested_at=datetime.fromisoformat(data["ingested_at"]),
        )


@dataclass(frozen=True, slots=True)
class Chunk:
    """A slice of a Document's text — the unit of retrieval.

    ``pages`` records the 1-indexed source page number(s) the text came from, so
    answers can cite pages.
    """

    text: str
    document_id: str
    pages: tuple[int, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class Citation:
    """Provenance for an answer: which Document, which page(s), and where on disk."""

    document_id: str
    document_name: str
    pages: tuple[int, ...]
    path: str


def utc_now() -> datetime:
    """Timezone-aware current time — the single clock source for ingest stamps."""
    return datetime.now(timezone.utc)
