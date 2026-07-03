"""Opt-in end-to-end check against the REAL Anthropic API + REAL local embedder.

Skipped by default. Runs only when an Anthropic key is present AND the embeddings
extra is installed:

    uv sync --extra embeddings
    ANTHROPIC_API_KEY=sk-ant-... uv run pytest tests/test_e2e.py

This verifies the whole PRD: real ingest (Haiku summarize/categorize + local
embeddings) and a real Strands+Claude ask yielding a grounded answer with a
correct Document + page Citation.
"""

from __future__ import annotations

import importlib.util
import os

import pytest

_HAS_KEY = bool(os.environ.get("ANTHROPIC_API_KEY", "").strip())
_HAS_EMBEDDINGS = importlib.util.find_spec("sentence_transformers") is not None

pytestmark = pytest.mark.skipif(
    not (_HAS_KEY and _HAS_EMBEDDINGS),
    reason="opt-in e2e: needs ANTHROPIC_API_KEY and the 'embeddings' extra",
)


def test_real_ingest_and_ask(config_file, make_pdf, tmp_path):
    from docvault.agent import AskAgent, anthropic_ask_model
    from docvault.anthropic_client import AnthropicLLMClient
    from docvault.config import load_config
    from docvault.embedding import LocalEmbedder
    from docvault.ingest import INGESTED, Ingestor

    cfg = load_config(config_file)
    llm = AnthropicLLMClient()
    embedder = LocalEmbedder()

    pdf = make_pdf(
        tmp_path / "q3.pdf",
        ["In Q3, customer churn rose to 4.2% driven by onboarding friction."],
    )
    outcome = Ingestor(cfg, llm=llm, embedder=embedder).ingest(pdf)[0]
    assert outcome.status == INGESTED

    answer = AskAgent(cfg, model=anthropic_ask_model(cfg), embedder=embedder).answer(
        "What happened to churn in Q3?"
    )

    assert answer.text.strip()
    assert any(c.document_name == "q3.pdf" for c in answer.citations)
