"""docvault — local, CLI-driven PDF knowledge base with agentic RAG over Claude.

See CONTEXT.md for the domain glossary and docs/adr/ for architectural decisions.
"""

from docvault.config import Config, load_config
from docvault.errors import ConfigError, DocVaultError, MissingApiKeyError
from docvault.types import Chunk, Citation, Document

__all__ = [
    "Config",
    "load_config",
    "Document",
    "Chunk",
    "Citation",
    "DocVaultError",
    "ConfigError",
    "MissingApiKeyError",
]
