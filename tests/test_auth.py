"""The single failure point for a missing Anthropic API key (story 33)."""

from __future__ import annotations

import pytest

from docvault.auth import require_api_key
from docvault.errors import MissingApiKeyError


def test_returns_key_when_set(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")

    assert require_api_key() == "sk-ant-test"


def test_raises_actionable_error_when_unset(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    with pytest.raises(MissingApiKeyError, match="ANTHROPIC_API_KEY"):
        require_api_key()


def test_blank_key_is_treated_as_missing(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "   ")

    with pytest.raises(MissingApiKeyError):
        require_api_key()
