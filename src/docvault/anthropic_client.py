"""Production LLM client: Claude via the official Anthropic SDK.

Implements the ``LLMClient`` boundary used by Ingest (summarize / categorize).
The Ask agent uses Strands' own Anthropic model (see agent.py). Exercised by the
opt-in end-to-end check (issue 10), not the offline suite.
"""

from __future__ import annotations

from docvault.auth import require_api_key

_MAX_TOKENS = 1024


class AnthropicLLMClient:
    """Calls Claude's Messages API and returns the concatenated text."""

    def __init__(self, api_key: str | None = None) -> None:
        key = api_key or require_api_key()  # fail fast, before importing the SDK
        import anthropic

        self._client = anthropic.Anthropic(api_key=key)

    def complete(self, *, model: str, prompt: str, system: str | None = None) -> str:
        kwargs = {
            "model": model,
            "max_tokens": _MAX_TOKENS,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            kwargs["system"] = system
        message = self._client.messages.create(**kwargs)
        return "".join(
            block.text
            for block in message.content
            if getattr(block, "type", None) == "text"
        )
