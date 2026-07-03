"""Shared fixtures."""

from __future__ import annotations

from pathlib import Path

import pymupdf
import pytest

from tests.fakes import FakeEmbedder, FakeLLMClient


def _write_pdf(path: Path, pages_text: list[str]) -> Path:
    """Create a born-digital PDF with the given text on each page."""
    doc = pymupdf.open()
    for text in pages_text:
        page = doc.new_page()
        if text:
            page.insert_text((72, 72), text, fontsize=12)
    doc.save(path)
    doc.close()
    return path


@pytest.fixture
def make_pdf():
    """Factory: make_pdf(path, ["page 1 text", ...]) -> Path."""
    def _factory(path: Path, pages_text: list[str]) -> Path:
        return _write_pdf(Path(path), pages_text)

    return _factory


@pytest.fixture
def born_digital_pdf(tmp_path: Path) -> Path:
    """A 2-page PDF with known, page-attributable text."""
    return _write_pdf(
        tmp_path / "born_digital.pdf",
        ["Alpha content about churn.", "Beta content about revenue."],
    )


@pytest.fixture
def empty_text_pdf(tmp_path: Path) -> Path:
    """A 1-page PDF with no text layer (stands in for a scan)."""
    return _write_pdf(tmp_path / "empty_text.pdf", [""])


@pytest.fixture
def fake_llm() -> FakeLLMClient:
    return FakeLLMClient()


@pytest.fixture
def fake_embedder() -> FakeEmbedder:
    return FakeEmbedder()


@pytest.fixture
def config_file(tmp_path: Path) -> Path:
    """A valid config file pointing its store root at a temp directory."""
    store_root = tmp_path / "store"
    path = tmp_path / "docvault.yaml"
    path.write_text(
        "store_root: {root}\n"
        "models:\n"
        "  ingest: claude-haiku-4-5\n"
        "  ask: claude-sonnet-5\n"
        "categories:\n"
        "  - invoices\n"
        "  - research\n".format(root=store_root)
    )
    return path
