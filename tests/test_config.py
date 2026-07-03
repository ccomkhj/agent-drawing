"""Behavior of configuration loading and the Category taxonomy."""

from __future__ import annotations

from pathlib import Path

import pytest

from docvault.config import (
    DEFAULT_ASK_MODEL,
    DEFAULT_INGEST_MODEL,
    UNCATEGORIZED,
    load_config,
)
from docvault.errors import ConfigError


def test_loads_valid_config(config_file: Path):
    cfg = load_config(config_file)

    assert cfg.ingest_model == "claude-haiku-4-5"
    assert cfg.ask_model == "claude-sonnet-5"
    assert cfg.categories == ("invoices", "research")
    assert cfg.store_root.name == "store"


def test_applies_defaults_for_omitted_fields(tmp_path: Path):
    path = tmp_path / "docvault.yaml"
    path.write_text("categories:\n  - misc\n")

    cfg = load_config(path)

    assert cfg.ingest_model == DEFAULT_INGEST_MODEL
    assert cfg.ask_model == DEFAULT_ASK_MODEL
    assert cfg.categories == ("misc",)


def test_empty_config_file_uses_all_defaults(tmp_path: Path):
    path = tmp_path / "docvault.yaml"
    path.write_text("")

    cfg = load_config(path)

    assert cfg.ingest_model == DEFAULT_INGEST_MODEL
    assert cfg.categories  # non-empty default taxonomy


def test_missing_file_raises_config_error(tmp_path: Path):
    with pytest.raises(ConfigError, match="not found"):
        load_config(tmp_path / "nope.yaml")


def test_malformed_yaml_raises_config_error(tmp_path: Path):
    path = tmp_path / "bad.yaml"
    path.write_text("categories: [unclosed\n")

    with pytest.raises(ConfigError, match="Malformed YAML"):
        load_config(path)


def test_non_mapping_config_raises(tmp_path: Path):
    path = tmp_path / "list.yaml"
    path.write_text("- just\n- a\n- list\n")

    with pytest.raises(ConfigError, match="must be a mapping"):
        load_config(path)


def test_empty_categories_list_raises(tmp_path: Path):
    path = tmp_path / "empty_cats.yaml"
    path.write_text("categories: []\n")

    with pytest.raises(ConfigError, match="must not be empty"):
        load_config(path)


def test_resolve_category_keeps_known_and_falls_back(config_file: Path):
    cfg = load_config(config_file)

    assert cfg.resolve_category("invoices") == "invoices"
    assert cfg.resolve_category("something-claude-made-up") == UNCATEGORIZED


def test_uncategorized_always_available(config_file: Path):
    cfg = load_config(config_file)

    assert UNCATEGORIZED in cfg.all_categories
    assert UNCATEGORIZED not in cfg.categories  # not silently added to the raw list


def test_store_paths_derive_from_root(config_file: Path):
    cfg = load_config(config_file)

    assert cfg.raw_dir == cfg.store_root / "raw"
    assert cfg.index_dir == cfg.store_root / "index"
    assert cfg.meta_dir == cfg.store_root / "meta"
