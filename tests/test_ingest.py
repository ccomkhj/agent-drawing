"""End-to-end ingest behavior through the seam (fake LLM + fake embedder,
real store + index + pymupdf on fixtures)."""

from __future__ import annotations

from pathlib import Path

from docvault.config import load_config
from docvault.index import VectorIndex
from docvault.ingest import FAILED, INGESTED, SKIPPED_DUPLICATE, Ingestor
from docvault.store import DocumentStore
from tests.fakes import FakeEmbedder, FakeLLMClient


def _ingestor(config_file: Path, llm: FakeLLMClient) -> Ingestor:
    return Ingestor(load_config(config_file), llm=llm, embedder=FakeEmbedder())


def test_single_file_files_under_category_and_indexes(config_file, born_digital_pdf):
    llm = FakeLLMClient(responses=["A concise summary.", "research"])
    ingestor = _ingestor(config_file, llm)

    outcomes = ingestor.ingest(born_digital_pdf)

    assert len(outcomes) == 1
    outcome = outcomes[0]
    assert outcome.status == INGESTED
    assert outcome.document.category == "research"
    assert outcome.document.summary == "A concise summary."

    cfg = load_config(config_file)
    stored = DocumentStore(cfg).get(outcome.document.id)
    assert stored.raw_path.parent.name == "research"
    assert VectorIndex(cfg).count() > 0  # chunks searchable


def test_folder_reports_per_file_outcomes_and_survives_a_bad_file(
    config_file, tmp_path, make_pdf
):
    folder = tmp_path / "inbox"
    folder.mkdir()
    make_pdf(folder / "good1.pdf", ["Content about invoices due."])
    make_pdf(folder / "good2.pdf", ["A research abstract."])
    make_pdf(folder / "scan.pdf", [""])  # empty text layer -> failure
    (folder / "notes.txt").write_text("not a pdf, ignored by *.pdf glob")

    llm = FakeLLMClient(default="research")
    outcomes = _ingestor(config_file, llm).ingest(folder)

    by_name = {o.path.name: o.status for o in outcomes}
    assert by_name == {
        "good1.pdf": INGESTED,
        "good2.pdf": INGESTED,
        "scan.pdf": FAILED,
    }
    # the bad file did not abort the batch: two documents landed
    assert len(DocumentStore(load_config(config_file)).list()) == 2


def test_reingesting_identical_file_is_skipped(config_file, born_digital_pdf):
    llm = FakeLLMClient(default="research")
    ingestor = _ingestor(config_file, llm)

    first = ingestor.ingest(born_digital_pdf)[0]
    second = ingestor.ingest(born_digital_pdf)[0]

    assert first.status == INGESTED
    assert second.status == SKIPPED_DUPLICATE
    cfg = load_config(config_file)
    assert len(DocumentStore(cfg).list()) == 1  # no second entry


def test_empty_text_pdf_is_a_clear_failure_not_indexed(config_file, empty_text_pdf):
    llm = FakeLLMClient(default="research")
    outcome = _ingestor(config_file, llm).ingest(empty_text_pdf)[0]

    assert outcome.status == FAILED
    assert outcome.document is None
    assert "born-digital" in outcome.error
    cfg = load_config(config_file)
    assert DocumentStore(cfg).list() == []
    assert VectorIndex(cfg).count() == 0


def test_llm_offlist_category_files_under_uncategorized(config_file, born_digital_pdf):
    llm = FakeLLMClient(responses=["summary", "cooking"])  # cooking not in taxonomy
    outcome = _ingestor(config_file, llm).ingest(born_digital_pdf)[0]

    assert outcome.document.category == "uncategorized"


def test_force_reingests_a_duplicate(config_file, born_digital_pdf):
    llm = FakeLLMClient(default="research")
    ingestor = _ingestor(config_file, llm)

    ingestor.ingest(born_digital_pdf)
    forced = ingestor.ingest(born_digital_pdf, force=True)[0]

    assert forced.status == INGESTED  # re-ran despite the duplicate hash
