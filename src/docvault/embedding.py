"""Local embedding model (ADR-0002): text in, vectors out, no external API.

sentence-transformers (and its torch backend) are heavy and only needed for real
runs, so they are an optional extra and imported lazily. The default/test path
uses the fake embedder through the seam; this real implementation is exercised by
the opt-in end-to-end check (issue 10).

Install with:  uv sync --extra embeddings
"""

from __future__ import annotations

from typing import Sequence

DEFAULT_MODEL = "BAAI/bge-small-en-v1.5"


class LocalEmbedder:
    """Embedder backed by a local sentence-transformers model."""

    def __init__(self, model_name: str = DEFAULT_MODEL) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:  # pragma: no cover - exercised only without extra
            raise ImportError(
                "Local embeddings need the 'embeddings' extra: "
                "uv sync --extra embeddings"
            ) from exc
        self._model_name = model_name
        self._model = SentenceTransformer(model_name)
        # method was renamed across sentence-transformers versions
        dim_fn = getattr(self._model, "get_embedding_dimension", None) or (
            self._model.get_sentence_embedding_dimension
        )
        self._dimension = int(dim_fn())

    @property
    def model_id(self) -> str:
        return self._model_name

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        vectors = self._model.encode(list(texts), normalize_embeddings=True)
        return [v.tolist() for v in vectors]
