"""Typed errors for docvault.

A small hierarchy so callers (and the CLI) can distinguish user-fixable problems
from bugs, and render actionable messages.
"""


class DocVaultError(Exception):
    """Base class for all docvault errors."""


class ConfigError(DocVaultError):
    """Configuration is missing, malformed, or invalid."""


class MissingApiKeyError(DocVaultError):
    """No Anthropic API key is available for a step that needs Claude."""


class ParseError(DocVaultError):
    """A PDF could not be read or is not a valid PDF."""


class EmptyTextError(DocVaultError):
    """A PDF has no extractable text layer (e.g. a scan).

    Out of scope for this PRD (born-digital only) — surfaced as a clear failure so
    nothing is silently indexed empty.
    """


class EmbeddingMismatchError(DocVaultError):
    """The embedder doesn't match the model/dimension the index was built with.

    Signals that a reindex is required (ADR-0002).
    """
