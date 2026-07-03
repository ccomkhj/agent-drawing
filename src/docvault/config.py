"""Editable configuration: the Category taxonomy, the two Claude models, and the
storage root.

Config lives in a single YAML file the user can edit. Everything has a sensible
default so a minimal (or empty) file still yields a usable Config.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from docvault.errors import ConfigError

#: Fallback Category for a Document that fits none of the configured ones.
UNCATEGORIZED = "uncategorized"

#: Default models (per ADR-0003 / PRD): cheap ingest, stronger ask.
DEFAULT_INGEST_MODEL = "claude-haiku-4-5"
DEFAULT_ASK_MODEL = "claude-sonnet-5"

DEFAULT_STORE_ROOT = "~/.docvault"
DEFAULT_CATEGORIES: tuple[str, ...] = (
    "invoices",
    "contracts",
    "research",
    "manuals",
    "personal",
)


@dataclass(frozen=True, slots=True)
class Config:
    """Resolved, validated configuration. Immutable."""

    store_root: Path
    ingest_model: str
    ask_model: str
    categories: tuple[str, ...]

    # --- Storage layout (derived from store_root) -----------------------------

    @property
    def raw_dir(self) -> Path:
        """Structured directory: raw PDFs filed by Category (organizational)."""
        return self.store_root / "raw"

    @property
    def index_dir(self) -> Path:
        """The vector index (primary retrieval — ADR-0001)."""
        return self.store_root / "index"

    @property
    def meta_dir(self) -> Path:
        """Per-Document metadata and Summaries."""
        return self.store_root / "meta"

    # --- Category handling ----------------------------------------------------

    @property
    def all_categories(self) -> tuple[str, ...]:
        """Configured categories plus the UNCATEGORIZED fallback (always present)."""
        if UNCATEGORIZED in self.categories:
            return self.categories
        return (*self.categories, UNCATEGORIZED)

    def resolve_category(self, label: str) -> str:
        """Constrain a proposed label to the taxonomy (fixed taxonomy decision).

        Returns the label if it is a configured Category, else UNCATEGORIZED.
        New categories are never invented at ingest.
        """
        return label if label in self.categories else UNCATEGORIZED


def load_config(path: str | Path) -> Config:
    """Load and validate configuration from a YAML file.

    Missing fields fall back to defaults. Raises ConfigError for a missing file,
    malformed YAML, or a structurally invalid document.
    """
    path = Path(path).expanduser()
    if not path.exists():
        raise ConfigError(f"Config file not found: {path}")

    try:
        raw = yaml.safe_load(path.read_text()) or {}
    except yaml.YAMLError as exc:
        raise ConfigError(f"Malformed YAML in {path}: {exc}") from exc

    if not isinstance(raw, dict):
        raise ConfigError(
            f"Config in {path} must be a mapping, got {type(raw).__name__}"
        )

    return _build_config(raw, path)


def _build_config(raw: dict, path: Path) -> Config:
    store_root = Path(str(raw.get("store_root", DEFAULT_STORE_ROOT))).expanduser()

    models = raw.get("models", {}) or {}
    if not isinstance(models, dict):
        raise ConfigError(f"'models' in {path} must be a mapping")
    ingest_model = str(models.get("ingest", DEFAULT_INGEST_MODEL))
    ask_model = str(models.get("ask", DEFAULT_ASK_MODEL))

    categories = _parse_categories(raw.get("categories", DEFAULT_CATEGORIES), path)

    return Config(
        store_root=store_root,
        ingest_model=ingest_model,
        ask_model=ask_model,
        categories=categories,
    )


def _parse_categories(value: object, path: Path) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        raise ConfigError(f"'categories' in {path} must be a list")
    categories = tuple(str(c).strip() for c in value if str(c).strip())
    if not categories:
        raise ConfigError(f"'categories' in {path} must not be empty")
    return categories
