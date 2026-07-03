"""Smoke tests for the thin CLI: formatting, command wiring with fakes, errors.

The pipeline itself is tested through the seam elsewhere; here we only check the
adapter renders/wires correctly."""

from __future__ import annotations

import pytest

from docvault.agent import Answer
from docvault.cli import (
    cmd_ask,
    cmd_ingest,
    cmd_list,
    format_answer,
    format_ingest,
    format_list,
    validate_ingest_path,
)
from docvault.config import load_config
from docvault.errors import DocVaultError, MissingApiKeyError
from docvault.ingest import FAILED, INGESTED, IngestOutcome
from docvault.types import Citation, Document, utc_now
from tests.fakes import FakeEmbedder, FakeLLMClient, ScriptedModel, text_turn, tool_turn


# --- formatting ---------------------------------------------------------------


def test_format_answer_includes_sources():
    answer = Answer(
        text="Churn rose 4%.",
        citations=(
            Citation("d1", "q3.pdf", (4,), "/store/raw/research/q3.pdf"),
        ),
    )

    out = format_answer(answer)

    assert "Churn rose 4%." in out
    assert "q3.pdf p.4" in out
    assert "/store/raw/research/q3.pdf" in out


def test_format_answer_without_citations_is_just_text():
    out = format_answer(Answer(text="Nothing relevant found.", citations=()))
    assert out == "Nothing relevant found."


def test_format_ingest_summarizes_outcomes(tmp_path):
    from pathlib import Path

    outcomes = [
        IngestOutcome(
            path=Path("a.pdf"),
            status=INGESTED,
            document=Document("i", "a.pdf", "research", "s", 1, "h", utc_now()),
        ),
        IngestOutcome(path=Path("b.pdf"), status=FAILED, error="No extractable text"),
    ]

    out = format_ingest(outcomes)

    assert "a.pdf: ingested → research" in out
    assert "b.pdf: failed — No extractable text" in out
    assert "1/2 ingested" in out


def test_format_list_groups_and_shows_summary():
    docs = [Document("i", "q3.pdf", "research", "Quarterly report.", 1, "h", utc_now())]
    out = format_list(docs)
    assert "[research] q3.pdf" in out
    assert "Quarterly report." in out


def test_format_list_empty():
    assert format_list([]) == "No documents ingested yet."


# --- command wiring (fakes) ---------------------------------------------------


def test_cmd_ingest_then_list(config_file, born_digital_pdf):
    cfg = load_config(config_file)
    out = cmd_ingest(
        config=cfg,
        llm=FakeLLMClient(responses=["a summary", "research"]),
        embedder=FakeEmbedder(),
        path=born_digital_pdf,
        force=False,
    )
    assert "ingested" in out

    listing = cmd_list(config=cfg)
    assert "[research]" in listing and "born_digital.pdf" in listing


def test_cmd_ask_renders_answer_and_opens_pdf(config_file, make_pdf, tmp_path):
    cfg = load_config(config_file)
    from docvault.ingest import Ingestor

    Ingestor(cfg, llm=FakeLLMClient(default="research"), embedder=FakeEmbedder()).ingest(
        make_pdf(tmp_path / "paper.pdf", ["churn analysis for Q3"])
    )

    opened: list[str] = []
    out = cmd_ask(
        config=cfg,
        model=ScriptedModel(
            [
                tool_turn("search_documents", {"query": "churn analysis for Q3"}),
                text_turn("Churn was analyzed."),
            ]
        ),
        embedder=FakeEmbedder(),
        question="churn?",
        do_open=True,
        opener=opened.append,
    )

    assert "Churn was analyzed." in out
    assert "Sources:" in out and "paper.pdf" in out
    assert opened and opened[0].endswith("paper.pdf")


# --- errors -------------------------------------------------------------------


def test_validate_ingest_path_missing(tmp_path):
    with pytest.raises(DocVaultError, match="Path not found"):
        validate_ingest_path(tmp_path / "nope.pdf")


def test_validate_ingest_path_non_pdf(tmp_path):
    junk = tmp_path / "notes.txt"
    junk.write_text("hi")
    with pytest.raises(DocVaultError, match="Not a PDF"):
        validate_ingest_path(junk)


def test_anthropic_client_missing_key_is_actionable(monkeypatch):
    from docvault.anthropic_client import AnthropicLLMClient

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(MissingApiKeyError):
        AnthropicLLMClient()
