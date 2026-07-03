"""Thin CLI adapter.

Holds no business logic — parses arguments, builds the real dependencies, and
calls the core library. Command handlers take injected dependencies so they can be
smoke-tested with fakes (the pipeline itself is tested elsewhere through the seam).
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import Callable

from docvault.agent import AskAgent, Answer, anthropic_ask_model
from docvault.boundaries import Embedder, LLMClient
from docvault.config import Config, load_config
from docvault.errors import DocVaultError
from docvault.ingest import FAILED, INGESTED, SKIPPED_DUPLICATE, IngestOutcome, Ingestor
from docvault.store import DocumentStore
from docvault.types import Document

DEFAULT_CONFIG = "docvault.yaml"
_STATUS_LABEL = {
    INGESTED: "ingested",
    SKIPPED_DUPLICATE: "skipped (duplicate)",
    FAILED: "failed",
}


# --- formatting (pure) --------------------------------------------------------


def format_ingest(outcomes: list[IngestOutcome]) -> str:
    lines = []
    for o in outcomes:
        label = _STATUS_LABEL.get(o.status, o.status)
        if o.status == INGESTED and o.document is not None:
            label += f" → {o.document.category}"
        elif o.status == FAILED and o.error:
            label += f" — {o.error}"
        lines.append(f"{o.path.name}: {label}")
    ingested = sum(1 for o in outcomes if o.status == INGESTED)
    lines.append(f"\n{ingested}/{len(outcomes)} ingested")
    return "\n".join(lines)


def format_answer(answer: Answer) -> str:
    lines = [answer.text]
    if answer.citations:
        lines += ["", "Sources:"]
        for c in answer.citations:
            pages = ",".join(map(str, c.pages)) or "?"
            lines.append(f"  - {c.document_name} p.{pages}")
            lines.append(f"    {c.path}")
    return "\n".join(lines)


def format_list(documents: list[Document]) -> str:
    if not documents:
        return "No documents ingested yet."
    lines = []
    for d in sorted(documents, key=lambda d: (d.category, d.source_filename)):
        lines.append(f"[{d.category}] {d.source_filename}")
        lines.append(f"    {d.summary}")
    return "\n".join(lines)


# --- command handlers (deps injected) -----------------------------------------


def cmd_ingest(
    *, config: Config, llm: LLMClient, embedder: Embedder, path: Path, force: bool
) -> str:
    validate_ingest_path(path)
    outcomes = Ingestor(config, llm=llm, embedder=embedder).ingest(path, force=force)
    return format_ingest(outcomes)


def cmd_ask(
    *,
    config: Config,
    model,
    embedder: Embedder,
    question: str,
    do_open: bool = False,
    opener: Callable[[str], None] | None = None,
) -> str:
    answer = AskAgent(config, model=model, embedder=embedder).answer(question)
    if do_open and answer.citations:
        (opener or open_pdf)(answer.citations[0].path)
    return format_answer(answer)


def cmd_list(*, config: Config) -> str:
    documents = [s.document for s in DocumentStore(config).list()]
    return format_list(documents)


def validate_ingest_path(path: Path) -> Path:
    if not path.exists():
        raise DocVaultError(f"Path not found: {path}")
    if path.is_file() and path.suffix.lower() != ".pdf":
        raise DocVaultError(f"Not a PDF: {path}")
    return path


def open_pdf(path: str) -> None:  # pragma: no cover - platform side effect
    if sys.platform == "darwin":
        subprocess.run(["open", path], check=False)
    elif sys.platform.startswith("linux"):
        subprocess.run(["xdg-open", path], check=False)
    elif sys.platform == "win32":
        os.startfile(path)  # type: ignore[attr-defined]


# --- argument parsing / wiring ------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="docvault", description=__doc__)
    parser.add_argument("--config", default=DEFAULT_CONFIG, help="path to config YAML")
    sub = parser.add_subparsers(dest="command", required=True)

    p_ingest = sub.add_parser("ingest", help="ingest a PDF or a folder of PDFs")
    p_ingest.add_argument("path")
    p_ingest.add_argument("--force", action="store_true", help="re-ingest duplicates")

    p_ask = sub.add_parser("ask", help="ask a question")
    p_ask.add_argument("question")
    p_ask.add_argument("--open", action="store_true", help="open the cited PDF")

    sub.add_parser("chat", help="interactive question loop")
    sub.add_parser("list", help="list ingested documents")
    return parser


def main(argv: list[str] | None = None) -> int:  # pragma: no cover - thin wiring
    argv = sys.argv[1:] if argv is None else argv
    args = _build_parser().parse_args(argv)
    try:
        config = load_config(args.config)
        return _dispatch(args, config)
    except DocVaultError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


def _dispatch(args, config: Config) -> int:  # pragma: no cover - thin wiring
    from docvault.anthropic_client import AnthropicLLMClient
    from docvault.embedding import LocalEmbedder

    if args.command == "ingest":
        path = validate_ingest_path(Path(args.path))  # fail fast before loading deps
        print(
            cmd_ingest(
                config=config,
                llm=AnthropicLLMClient(),
                embedder=LocalEmbedder(),
                path=path,
                force=args.force,
            )
        )
    elif args.command == "ask":
        print(
            cmd_ask(
                config=config,
                model=anthropic_ask_model(config),
                embedder=LocalEmbedder(),
                question=args.question,
                do_open=args.open,
            )
        )
    elif args.command == "chat":
        _chat(config)
    elif args.command == "list":
        print(cmd_list(config=config))
    return 0


def _chat(config: Config) -> None:  # pragma: no cover - interactive loop
    model = anthropic_ask_model(config)
    embedder = LocalEmbedder()
    print("Ask questions about your documents. Blank line or Ctrl-D to quit.")
    while True:
        try:
            question = input("> ").strip()
        except EOFError:
            break
        if not question:
            break
        print(cmd_ask(config=config, model=model, embedder=embedder, question=question))


if __name__ == "__main__":
    raise SystemExit(main())
