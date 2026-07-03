"""Behavior of the Ingest LLM steps, driven through the seam with a fake LLM."""

from __future__ import annotations

from pathlib import Path

from docvault.config import UNCATEGORIZED, load_config
from docvault.enrichment import categorize, summarize
from tests.fakes import FakeLLMClient


def test_summarize_returns_model_text_using_ingest_model(config_file: Path):
    cfg = load_config(config_file)
    llm = FakeLLMClient(responses=["A short summary."])

    result = summarize("long body text", llm=llm, model=cfg.ingest_model)

    assert result == "A short summary."
    assert llm.calls[0]["model"] == "claude-haiku-4-5"


def test_categorize_returns_configured_category(config_file: Path):
    cfg = load_config(config_file)  # categories: invoices, research
    llm = FakeLLMClient(responses=["research"])

    assert categorize("a paper", llm=llm, config=cfg) == "research"
    assert llm.calls[0]["model"] == cfg.ingest_model


def test_categorize_normalizes_case_and_punctuation(config_file: Path):
    cfg = load_config(config_file)
    llm = FakeLLMClient(responses=["  Research.  "])

    assert categorize("a paper", llm=llm, config=cfg) == "research"


def test_categorize_off_list_falls_back_to_uncategorized(config_file: Path):
    cfg = load_config(config_file)
    llm = FakeLLMClient(responses=["cooking"])  # not in the taxonomy

    assert categorize("a recipe", llm=llm, config=cfg) == UNCATEGORIZED


def test_categorize_prompt_lists_the_taxonomy(config_file: Path):
    cfg = load_config(config_file)
    llm = FakeLLMClient(responses=["invoices"])

    categorize("an invoice", llm=llm, config=cfg)

    prompt = llm.calls[0]["prompt"]
    assert "invoices" in prompt and "research" in prompt
