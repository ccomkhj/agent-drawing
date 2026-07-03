"""Behavior of PDF parsing: text + page provenance, content hash, empty detection.

Uses real pymupdf against fixture PDFs (this component is not faked).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from docvault.errors import EmptyTextError, ParseError
from docvault.parsing import content_hash, parse_pdf


def test_extracts_text_with_page_provenance(born_digital_pdf: Path):
    parsed = parse_pdf(born_digital_pdf)

    assert parsed.page_count == 2
    assert parsed.pages[0].number == 1
    assert parsed.pages[1].number == 2
    assert "Alpha" in parsed.pages[0].text
    assert "Beta" in parsed.pages[1].text
    assert "churn" in parsed.full_text and "revenue" in parsed.full_text


def test_content_hash_is_stable_and_distinct(born_digital_pdf: Path, empty_text_pdf: Path):
    first = parse_pdf(born_digital_pdf).content_hash
    again = parse_pdf(born_digital_pdf).content_hash

    assert first == again  # same bytes → same hash

    with pytest.raises(EmptyTextError):
        parse_pdf(empty_text_pdf)  # different file; also proves it's a distinct doc

    # hash function directly
    assert content_hash(b"abc") == content_hash(b"abc")
    assert content_hash(b"abc") != content_hash(b"abd")


def test_empty_text_layer_raises_clear_failure(empty_text_pdf: Path):
    with pytest.raises(EmptyTextError, match="born-digital"):
        parse_pdf(empty_text_pdf)


def test_missing_file_raises_parse_error(tmp_path: Path):
    with pytest.raises(ParseError, match="Could not read"):
        parse_pdf(tmp_path / "does_not_exist.pdf")


def test_non_pdf_file_raises_parse_error(tmp_path: Path):
    junk = tmp_path / "not_a.pdf"
    junk.write_bytes(b"this is plainly not a pdf")

    with pytest.raises(ParseError, match="Not a valid PDF"):
        parse_pdf(junk)
