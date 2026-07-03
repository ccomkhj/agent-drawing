"""The document store: files raw PDFs into the Structured directory by Category,
persists Document metadata + Summary, and supports deduplication by content hash.

Raw PDFs are always retained (enables rebuild — ADR-0002). The Structured
directory is organizational only; retrieval uses the vector index (ADR-0001).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from docvault.config import Config
from docvault.types import Document


@dataclass(frozen=True, slots=True)
class StoredDocument:
    """A persisted Document plus where its raw PDF lives on disk."""

    document: Document
    raw_path: Path


class DocumentStore:
    """Filesystem-backed store under the configured store root."""

    def __init__(self, config: Config) -> None:
        self._raw_dir = config.raw_dir
        self._meta_dir = config.meta_dir
        self._store_root = config.store_root

    # --- writes ---------------------------------------------------------------

    def save(self, document: Document, pdf_bytes: bytes) -> StoredDocument:
        """File the raw PDF under its Category and persist its metadata.

        Re-saving the same Document id overwrites in place (idempotent) — it does
        not create a second entry.
        """
        dest_dir = self._raw_dir / document.category
        dest_dir.mkdir(parents=True, exist_ok=True)
        raw_path = self._resolve_raw_path(document, dest_dir)
        raw_path.write_bytes(pdf_bytes)

        self._meta_dir.mkdir(parents=True, exist_ok=True)
        record = {
            "document": document.to_dict(),
            "raw_relpath": str(raw_path.relative_to(self._store_root)),
        }
        self._meta_path(document.id).write_text(json.dumps(record, indent=2))
        return StoredDocument(document=document, raw_path=raw_path)

    # --- reads ----------------------------------------------------------------

    def get(self, doc_id: str) -> StoredDocument | None:
        path = self._meta_path(doc_id)
        if not path.exists():
            return None
        return self._load(path)

    def find_by_hash(self, content_hash: str) -> StoredDocument | None:
        """Return an existing StoredDocument with this content hash, if any."""
        for stored in self.list():
            if stored.document.content_hash == content_hash:
                return stored
        return None

    def list(self) -> list[StoredDocument]:
        if not self._meta_dir.exists():
            return []
        return [self._load(p) for p in sorted(self._meta_dir.glob("*.json"))]

    # --- internals ------------------------------------------------------------

    def _meta_path(self, doc_id: str) -> Path:
        return self._meta_dir / f"{doc_id}.json"

    def _load(self, path: Path) -> StoredDocument:
        record = json.loads(path.read_text())
        document = Document.from_dict(record["document"])
        raw_path = self._store_root / record["raw_relpath"]
        return StoredDocument(document=document, raw_path=raw_path)

    def _resolve_raw_path(self, document: Document, dest_dir: Path) -> Path:
        """Pick a filename under dest_dir, disambiguating filename collisions
        between *different* Documents with a short content-hash suffix."""
        candidate = dest_dir / document.source_filename
        if not candidate.exists() or self._same_document(candidate, document):
            return candidate
        stem, suffix = candidate.stem, candidate.suffix
        return dest_dir / f"{stem}-{document.content_hash[:8]}{suffix}"

    def _same_document(self, raw_path: Path, document: Document) -> bool:
        existing = self.get(document.id)
        return existing is not None and existing.raw_path == raw_path
