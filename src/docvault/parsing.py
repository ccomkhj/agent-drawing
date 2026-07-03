"""PDF parsing: extract born-digital text with page provenance, compute the
content hash, and detect an empty text layer.

This is the real (un-faked) front of the Ingest pipeline (ADR-0001). Scanned /
image-only PDFs are out of scope — an empty text layer is surfaced as
``EmptyTextError`` rather than indexed empty.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import pymupdf

from docvault.errors import EmptyTextError, ParseError

#: A parse yielding fewer than this many non-whitespace characters across the
#: whole document is treated as having no usable text layer.
MIN_MEANINGFUL_CHARS = 1


@dataclass(frozen=True, slots=True)
class PageText:
    """Text extracted from one page. ``number`` is 1-indexed."""

    number: int
    text: str


@dataclass(frozen=True, slots=True)
class ParsedDocument:
    """The result of parsing one PDF, before summarize/categorize/chunk."""

    pages: tuple[PageText, ...]
    content_hash: str

    @property
    def page_count(self) -> int:
        return len(self.pages)

    @property
    def full_text(self) -> str:
        """All page text joined in reading order."""
        return "\n".join(page.text for page in self.pages)


def content_hash(data: bytes) -> str:
    """Stable content hash of raw PDF bytes (used for deduplication)."""
    return hashlib.sha256(data).hexdigest()


def parse_pdf(path: str | Path) -> ParsedDocument:
    """Parse a born-digital PDF into per-page text plus its content hash.

    Raises:
        ParseError: the file is missing, unreadable, or not a valid PDF.
        EmptyTextError: the PDF has no extractable text layer.
    """
    path = Path(path)
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise ParseError(f"Could not read PDF: {path} ({exc})") from exc

    digest = content_hash(data)

    try:
        with pymupdf.open(stream=data, filetype="pdf") as doc:
            pages = tuple(
                PageText(number=i + 1, text=page.get_text().strip())
                for i, page in enumerate(doc)
            )
    except (pymupdf.FileDataError, ValueError, RuntimeError) as exc:
        raise ParseError(f"Not a valid PDF: {path} ({exc})") from exc

    _require_text(pages, path)
    return ParsedDocument(pages=pages, content_hash=digest)


def _require_text(pages: tuple[PageText, ...], path: Path) -> None:
    total = sum(len(page.text) for page in pages)
    if total < MIN_MEANINGFUL_CHARS:
        raise EmptyTextError(
            f"No extractable text in {path.name} — scanned/image PDFs are not "
            f"supported (born-digital only)."
        )
