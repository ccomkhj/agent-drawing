"""Anthropic credential resolution — the single, clean failure point for a
missing API key (PRD story 33).

The concrete raising lives here so every Claude-backed step (Ingest summarize /
categorize, the Ask agent) can require credentials the same way and surface one
actionable error.
"""

from __future__ import annotations

import os

from docvault.errors import MissingApiKeyError

_ENV_VAR = "ANTHROPIC_API_KEY"


def require_api_key() -> str:
    """Return the Anthropic API key, or raise MissingApiKeyError with guidance."""
    key = os.environ.get(_ENV_VAR, "").strip()
    if not key:
        raise MissingApiKeyError(
            f"No Anthropic API key found. Set the {_ENV_VAR} environment variable "
            f"(export {_ENV_VAR}=sk-ant-...) before ingesting or asking."
        )
    return key
