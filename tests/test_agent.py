"""The Ask agent, driven offline through the real Strands loop with a scripted
model plus real tools/retriever/index (seeded via ingest)."""

from __future__ import annotations

from docvault.agent import AskAgent
from docvault.config import load_config
from docvault.ingest import Ingestor
from docvault.retrieval import Retriever
from tests.fakes import FakeEmbedder, FakeLLMClient, ScriptedModel, text_turn, tool_turn


def _seed(config_file, make_pdf, tmp_path) -> None:
    llm = FakeLLMClient(responses=["summary", "research", "summary", "invoices"])
    ingestor = Ingestor(load_config(config_file), llm=llm, embedder=FakeEmbedder())
    ingestor.ingest(make_pdf(tmp_path / "paper.pdf", ["churn analysis for Q3"]))
    ingestor.ingest(make_pdf(tmp_path / "bill.pdf", ["invoice total due amount"]))


def _agent(config_file, turns) -> AskAgent:
    return AskAgent(
        load_config(config_file), model=ScriptedModel(turns), embedder=FakeEmbedder()
    )


def test_grounded_answer_carries_citation_to_correct_document_and_page(
    config_file, make_pdf, tmp_path
):
    _seed(config_file, make_pdf, tmp_path)
    turns = [
        tool_turn("search_documents", {"query": "churn analysis for Q3"}),
        text_turn("Churn was analyzed for Q3."),
    ]

    answer = _agent(config_file, turns).answer("what about churn?")

    assert "Churn was analyzed" in answer.text
    # Citations are the retrieved hits, most-relevant first; the exact-match query
    # makes paper.pdf the top hit.
    top = answer.citations[0]
    assert top.document_name == "paper.pdf"
    assert top.pages == (1,)


def test_agent_can_search_more_than_once_and_narrow_by_category(
    config_file, make_pdf, tmp_path
):
    _seed(config_file, make_pdf, tmp_path)
    turns = [
        tool_turn("search_documents", {"query": "churn analysis for Q3"}),
        tool_turn(
            "search_documents",
            {"query": "invoice total due amount", "category": "invoices"},
        ),
        text_turn("Combined answer."),
    ]

    answer = _agent(config_file, turns).answer("compare churn and invoices")

    names = {c.document_name for c in answer.citations}
    assert names == {"paper.pdf", "bill.pdf"}  # both searches contributed


def test_empty_retrieval_yields_no_citations(config_file):
    # No documents ingested → search returns nothing → no fabricated citations.
    turns = [
        tool_turn("search_documents", {"query": "anything"}),
        text_turn("I couldn't find anything relevant in your documents."),
    ]

    answer = _agent(config_file, turns).answer("anything?")

    assert answer.citations == ()
    assert "couldn't find anything relevant" in answer.text


def test_agent_can_read_a_full_document(config_file, make_pdf, tmp_path):
    _seed(config_file, make_pdf, tmp_path)
    doc_id = Retriever(load_config(config_file), embedder=FakeEmbedder()).search(
        "churn analysis for Q3"
    )[0].document_id
    turns = [
        tool_turn("read_full_pdf", {"document_id": doc_id}),
        text_turn("Summarized from the full document."),
    ]

    answer = _agent(config_file, turns).answer("summarize the churn paper")

    assert "Summarized from the full document." in answer.text
