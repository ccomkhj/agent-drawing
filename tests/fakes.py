"""Test doubles for the two injectable boundaries.

Injected into the core in place of the real Anthropic SDK and embedding model so
the suite is fast, deterministic, and offline. Reused by every later issue's
tests through the single seam.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Sequence

from strands.models import Model


@dataclass
class FakeLLMClient:
    """Canned Claude. Returns queued responses (or a default) and records calls.

    ``responses`` are returned in order; once exhausted, ``default`` is returned.
    """

    responses: list[str] = field(default_factory=list)
    default: str = ""
    calls: list[dict] = field(default_factory=list)

    def complete(self, *, model: str, prompt: str, system: str | None = None) -> str:
        self.calls.append({"model": model, "prompt": prompt, "system": system})
        if self.responses:
            return self.responses.pop(0)
        return self.default


@dataclass
class FakeEmbedder:
    """Deterministic embedder: same text always maps to the same vector.

    Vectors are derived from a hash of the text so retrieval ordering is
    predictable in tests without a real model.
    """

    model_id_value: str = "fake-embedder-v1"
    dimension_value: int = 8

    @property
    def model_id(self) -> str:
        return self.model_id_value

    @property
    def dimension(self) -> int:
        return self.dimension_value

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        return [self._vector(t) for t in texts]

    def _vector(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        return [digest[i % len(digest)] / 255.0 for i in range(self.dimension_value)]


def text_turn(text: str) -> dict:
    """A scripted assistant turn that emits final text."""
    return {"kind": "text", "text": text}


def tool_turn(name: str, tool_input: dict) -> dict:
    """A scripted assistant turn that calls one tool."""
    return {"kind": "tool", "name": name, "input": tool_input}


class ScriptedModel(Model):
    """A Strands ``Model`` that replays scripted turns to drive the agent loop
    offline and deterministically.

    Each call to ``stream()`` (one model turn) consumes the next scripted turn:
    a ``tool_turn`` yields a tool_use turn (Strands then runs the tool and calls
    stream again); a ``text_turn`` yields the final answer.
    """

    def __init__(self, turns: list[dict]) -> None:
        self._turns = list(turns)
        self._config: dict[str, Any] = {}

    # -- Model interface -------------------------------------------------------

    def update_config(self, **model_config: Any) -> None:
        self._config.update(model_config)

    def get_config(self) -> dict[str, Any]:
        return self._config

    async def structured_output(self, *args: Any, **kwargs: Any):
        raise NotImplementedError("ScriptedModel does not support structured_output")
        yield  # pragma: no cover - makes this an async generator

    async def stream(self, messages, tool_specs=None, system_prompt=None, **kwargs):
        turn = self._turns.pop(0) if self._turns else text_turn("")
        if turn["kind"] == "tool":
            async for event in self._tool_events(turn):
                yield event
        else:
            async for event in self._text_events(turn):
                yield event

    # -- event emission --------------------------------------------------------

    async def _text_events(self, turn: dict):
        yield {"messageStart": {"role": "assistant"}}
        yield {"contentBlockStart": {"start": {}}}
        yield {"contentBlockDelta": {"delta": {"text": turn["text"]}}}
        yield {"contentBlockStop": {}}
        yield {"messageStop": {"stopReason": "end_turn"}}
        yield {"metadata": {"usage": {"inputTokens": 1, "outputTokens": 1, "totalTokens": 2}, "metrics": {"latencyMs": 0}}}

    async def _tool_events(self, turn: dict):
        yield {"messageStart": {"role": "assistant"}}
        yield {
            "contentBlockStart": {
                "start": {"toolUse": {"name": turn["name"], "toolUseId": "tool-1"}}
            }
        }
        yield {"contentBlockDelta": {"delta": {"toolUse": {"input": json.dumps(turn["input"])}}}}
        yield {"contentBlockStop": {}}
        yield {"messageStop": {"stopReason": "tool_use"}}
