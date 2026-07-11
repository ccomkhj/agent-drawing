"""The Ask agent (ADR-0003): a Strands agent equipped with the three retrieval
tools, producing a grounded Answer with Citations.

The Strands ``Model`` is the injectable boundary for the ask loop — tests inject a
scripted model to drive the real agent loop offline; production injects an
Anthropic-backed model. Citation assembly and the grounded-answer contract are our
code (tested deterministically); the model only chooses which tools to call.
"""

from __future__ import annotations

from dataclasses import dataclass

from strands import Agent, tool
from strands.models import Model

from docvault.boundaries import Embedder
from docvault.config import Config
from docvault.corpus import Corpus, SearchHit
from docvault.types import Citation

_SYSTEM_PROMPT = (
    "You answer questions using ONLY the user's own document collection. "
    "Use the search_documents tool to find relevant passages; you may search more "
    "than once, narrow by category, or read a full document by id when passages are "
    "insufficient. Ground every claim in retrieved passages and never invent facts. "
    "If searches return nothing relevant, say you could not find anything relevant "
    "in the documents rather than answering from general knowledge. Cite the source "
    "document and page(s) you relied on."
)


@dataclass(frozen=True, slots=True)
class Answer:
    """The agent's response: the text plus the Citations it drew on."""

    text: str
    citations: tuple[Citation, ...]


class AskAgent:
    """Builds and runs a Strands agent over the retrieval tools."""

    def __init__(self, config: Config, *, model: Model, embedder: Embedder) -> None:
        self._config = config
        self._model = model
        self._corpus = Corpus(config, embedder=embedder)

    def answer(self, question: str) -> Answer:
        collected: list[SearchHit] = []
        agent = Agent(
            model=self._model,
            tools=_build_tools(self._corpus, self._config, collected),
            system_prompt=_SYSTEM_PROMPT,
        )
        result = agent(question)
        return Answer(text=str(result).strip(), citations=_citations(collected))


def _build_tools(corpus: Corpus, config: Config, collected: list[SearchHit]) -> list:
    """The three tools, closed over the corpus, the taxonomy, and a collector."""

    @tool
    def search_documents(query: str, category: str | None = None) -> str:
        """Search the document collection for passages relevant to a query.

        Args:
            query: What to look for, in natural language.
            category: Optional category name to restrict the search to.
        """
        hits = corpus.search(query, category=category)
        collected.extend(hits)
        if not hits:
            return "No relevant passages found."
        return "\n\n".join(
            f"[document_id={h.document_id} | {h.document_name} "
            f"p.{','.join(map(str, h.pages))}] {h.text}"
            for h in hits
        )

    @tool
    def list_categories() -> str:
        """List the document categories available in the collection."""
        return ", ".join(config.categories)

    @tool
    def read_full_pdf(document_id: str) -> str:
        """Read the full text of one document, identified by its document_id.

        Args:
            document_id: The id shown in search_documents results.
        """
        text = corpus.read_full(document_id)
        return text if text is not None else f"No document with id {document_id}."

    return [search_documents, list_categories, read_full_pdf]


def _citations(hits: list[SearchHit]) -> tuple[Citation, ...]:
    """Deduplicate collected hits into Citations, preserving first-seen order."""
    seen: set[tuple[str, tuple[int, ...]]] = set()
    citations: list[Citation] = []
    for hit in hits:
        key = (hit.document_id, hit.pages)
        if key in seen:
            continue
        seen.add(key)
        citations.append(hit.citation())
    return tuple(citations)


def anthropic_ask_model(config: Config, *, max_tokens: int = 4096) -> Model:
    """Production model: Claude (Ask model from config) via Strands' provider.

    Exercised by the opt-in end-to-end check (issue 10), not the offline suite.
    """
    from strands.models.anthropic import AnthropicModel

    from docvault.auth import require_api_key

    return AnthropicModel(
        client_args={"api_key": require_api_key()},
        model_id=config.ask_model,
        max_tokens=max_tokens,
    )
