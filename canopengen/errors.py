"""User-facing CanOpenGen diagnostics."""

from __future__ import annotations

from pathlib import Path
from typing import Any


class CanOpenGenError(Exception):
    """Base class for expected, user-facing CanOpenGen failures."""


class ParseError(CanOpenGenError):
    """A source file could not be read or decoded as YAML."""

    def __init__(self, path: Path, message: str, *, line: int | None = None) -> None:
        """Create a parse diagnostic for a source path and optional one-based line."""
        self.path = path
        self.message = message
        self.line = line
        location = f"{path}:{line}" if line is not None else str(path)
        super().__init__(f"{location}: {message}")


class UnsupportedSchemaVersionError(CanOpenGenError):
    """A YAML document uses a schema version this build cannot parse."""

    def __init__(self, path: Path, version: Any) -> None:
        """Create a version diagnostic that identifies the supported version."""
        self.path = path
        self.version = version
        if version is None:
            detail = "missing required 'schema' version; add 'schema: 1'"
        else:
            detail = f"unsupported schema version {version!r}; supported versions: 1"
        super().__init__(f"{path}: {detail}")


class SchemaValidationError(CanOpenGenError):
    """A decoded YAML document does not conform to the public JSON Schema."""

    def __init__(self, path: Path, field_path: str, message: str) -> None:
        """Create a structural diagnostic at a dotted YAML field path."""
        self.path = path
        self.field_path = field_path
        self.message = message
        location = f"{path}: {field_path}" if field_path else str(path)
        super().__init__(f"{location}: {message}")


class CommandUnavailableError(CanOpenGenError):
    """A stable CLI command exists but its implementation belongs to a later phase."""
