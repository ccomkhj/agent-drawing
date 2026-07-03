"""Chunking: split a parsed Document into Chunks that carry page provenance.

Chunking is done per page, so every Chunk maps to exactly one source page and
answers can cite it precisely. Long pages are split into overlapping windows.
"""

from __future__ import annotations

from docvault.parsing import ParsedDocument
from docvault.types import Chunk

DEFAULT_MAX_CHARS = 800
DEFAULT_OVERLAP = 150


def chunk_document(
    parsed: ParsedDocument,
    document_id: str,
    *,
    max_chars: int = DEFAULT_MAX_CHARS,
    overlap: int = DEFAULT_OVERLAP,
) -> list[Chunk]:
    """Split each page's text into overlapping Chunks tagged with its page number."""
    chunks: list[Chunk] = []
    for page in parsed.pages:
        text = page.text.strip()
        if not text:
            continue
        for window in _windows(text, max_chars, overlap):
            chunks.append(
                Chunk(text=window, document_id=document_id, pages=(page.number,))
            )
    return chunks


def _windows(text: str, max_chars: int, overlap: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    step = max(1, max_chars - overlap)
    return [text[i : i + max_chars] for i in range(0, len(text), step)]
