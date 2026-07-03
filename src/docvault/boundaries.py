"""The two injectable external boundaries — the single test seam.

Core logic depends only on these protocols, never on a hard import of the
Anthropic SDK or an embedding library. Production wires in real implementations;
tests inject fakes (see tests/fakes.py). This is what keeps the suite fast,
deterministic, and offline (PRD Testing Decisions).
"""

from __future__ import annotations

from typing import Protocol, Sequence, runtime_checkable


@runtime_checkable
class LLMClient(Protocol):
    """A minimal Claude interface: given a prompt, return the model's text.

    Used for Ingest (summarize / categorize) and by the Ask agent's model calls.
    """

    def complete(
        self, *, model: str, prompt: str, system: str | None = None
    ) -> str: ...


@runtime_checkable
class Embedder(Protocol):
    """A local embedding model (ADR-0002): text in, vectors out.

    ``model_id`` and ``dimension`` are recorded alongside the index so a mismatch
    is detectable on reindex.
    """

    @property
    def model_id(self) -> str: ...

    @property
    def dimension(self) -> int: ...

    def embed(self, texts: Sequence[str]) -> list[list[float]]: ...
