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
    """A stable CLI command exists but is unavailable in this build."""


class AllocationError(CanOpenGenError):
    """Base class for deterministic Object Dictionary allocation failures."""


class DuplicateQualifiedNameError(AllocationError):
    """Two allocation inputs use the same semantic identity."""


class ExplicitIndexOutOfRangeError(AllocationError):
    """An explicit object index is outside its schema-v1 category partition."""


class ExplicitIndexCollisionError(AllocationError):
    """Two explicit object indexes select the same CANopen address."""


class IndexRangeExhaustedError(AllocationError):
    """A category has no remaining automatic index slot."""


class ExplicitSubindexOutOfRangeError(AllocationError):
    """An explicit record field subindex is outside 1 through 254."""


class ExplicitSubindexCollisionError(AllocationError):
    """Two record fields select the same explicit subindex."""


class RecordSubindexExhaustedError(AllocationError):
    """A record contains more fields than its usable subindex space."""


class InvalidArrayLengthError(AllocationError):
    """An array cannot fit in the sequential CANopen subindex space."""


class UnknownAddressObjectError(AllocationError):
    """An address diagnostic context does not contain the requested object."""


class TypeResolutionError(CanOpenGenError):
    """Base class for custom and object datatype resolution failures."""


class UnknownDataTypeError(TypeResolutionError):
    """A custom base, object, field, or array item names no known datatype."""


class AliasCycleError(TypeResolutionError):
    """Custom aliases form a recursive dependency chain."""


class InvalidEnumBaseError(TypeResolutionError):
    """An enum does not ultimately resolve to an integer CANopen primitive."""


class EnumValueOutOfRangeError(TypeResolutionError):
    """An enum value does not fit its resolved integer primitive."""


class ReservedTypeNameError(TypeResolutionError):
    """A custom type shadows a primitive or structural schema type name."""


class AmbiguousDataTypeError(TypeResolutionError):
    """An unqualified datatype matches declarations in multiple visible modules."""


class ModuleResolutionError(CanOpenGenError):
    """Base class for reusable-module dependency and reference failures."""


class UnknownModuleError(ModuleResolutionError):
    """A module import has no matching ``Modules/<name>.yml`` source file."""


class InvalidModuleNameError(ModuleResolutionError):
    """A module import is not a safe filename-stem namespace."""


class DuplicateModuleImportError(ModuleResolutionError):
    """One definition directly imports the same module more than once."""


class ModuleDependencyCycleError(ModuleResolutionError):
    """Recursive module imports form a dependency cycle."""


class ModuleParameterConflictError(ModuleResolutionError):
    """A module is reached with incompatible parameter assignments."""


class NamespaceCollisionError(ModuleResolutionError):
    """A device and one of its modules use the same identity namespace."""


class ReferenceResolutionError(ModuleResolutionError):
    """Base class for symbolic Object Dictionary reference failures."""


class UnknownReferenceError(ReferenceResolutionError):
    """A symbolic reference matches no visible object or record field."""


class AmbiguousReferenceError(ReferenceResolutionError):
    """An unqualified reference matches multiple visible qualified names."""


class PdoValidationError(CanOpenGenError):
    """A resolved PDO mapping cannot be represented by classic CANopen PDOs."""


class EdsGenerationError(CanOpenGenError):
    """The resolved Object Dictionary cannot be rendered as compatible EDS."""


class MarkdownGenerationError(CanOpenGenError):
    """The resolved Object Dictionary cannot be rendered as device documentation."""


class CppGenerationError(CanOpenGenError):
    """The resolved Object Dictionary cannot be rendered as C++ metadata."""


class Eds2OdError(CanOpenGenError):
    """Base class for Eds2Od discovery and execution failures."""


class Eds2OdUnavailableError(Eds2OdError):
    """No usable bundled or explicitly supplied Eds2Od invocation is available."""


class Eds2OdExecutionError(Eds2OdError):
    """Eds2Od rejected an EDS or did not produce the requested C++ output."""
