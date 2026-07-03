"""Ingest LLM steps: generate a Summary and assign a Category.

Both call Claude through the injected ``LLMClient`` (the Ingest model, Haiku by
default), never a hard SDK import — this keeps the step inside the test seam.
Categorization is constrained to the fixed taxonomy (ADR / PRD): the model picks
one configured Category, and anything off-list falls back to ``uncategorized``.
New categories are never invented.
"""

from __future__ import annotations

from docvault.boundaries import LLMClient
from docvault.config import UNCATEGORIZED, Config

_SUMMARY_SYSTEM = (
    "You write concise, factual summaries of documents. Respond with 2-4 sentences "
    "capturing what the document is and what it covers. No preamble."
)

_CATEGORY_SYSTEM = (
    "You classify a document into exactly one category from a fixed list. "
    "Respond with only the single category name, exactly as written in the list, "
    "and nothing else."
)


def summarize(text: str, *, llm: LLMClient, model: str) -> str:
    """Produce a concise Summary of the Document text."""
    prompt = f"Summarize the following document:\n\n{text}"
    return llm.complete(model=model, prompt=prompt, system=_SUMMARY_SYSTEM).strip()


def categorize(text: str, *, llm: LLMClient, config: Config) -> str:
    """Assign exactly one Category from the fixed taxonomy (else UNCATEGORIZED)."""
    options = "\n".join(f"- {c}" for c in config.categories)
    prompt = (
        f"Categories:\n{options}\n\n"
        f"Classify this document into one of the categories above:\n\n{text}"
    )
    raw = llm.complete(model=config.ingest_model, prompt=prompt, system=_CATEGORY_SYSTEM)
    return _match_category(raw, config.categories)


def _match_category(raw: str, categories: tuple[str, ...]) -> str:
    """Normalize the model's answer and match it (case-insensitively) to the list."""
    cleaned = raw.strip().strip("\"'").rstrip(".").strip().lower()
    for category in categories:
        if category.lower() == cleaned:
            return category
    return UNCATEGORIZED
