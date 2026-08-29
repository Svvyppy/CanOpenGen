"""CANopen primitive and custom datatype declarations."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final


@dataclass(frozen=True, slots=True)
class PrimitiveDataType:
    """Metadata for one developer-facing CANopen primitive alias.

    Numeric EDS datatype identifiers are intentionally absent. They will be added only
    after the bundled Eds2Od implementation is inspected in Phase 5.
    """

    alias: str
    canopen_name: str
    bit_width: int | None
    integer_range: tuple[int, int] | None = None
    pdo_mappable: bool = True

    @property
    def is_integer(self) -> bool:
        """Return whether enum range validation can use this primitive."""
        return self.integer_range is not None


def _integer(alias: str, canopen_name: str, bits: int, *, signed: bool) -> PrimitiveDataType:
    """Build integer primitive metadata without duplicating range arithmetic."""
    if signed:
        lower = -(1 << (bits - 1))
        upper = (1 << (bits - 1)) - 1
    else:
        lower = 0
        upper = (1 << bits) - 1
    return PrimitiveDataType(alias, canopen_name, bits, (lower, upper))


_PRIMITIVES = {
    "bool": PrimitiveDataType("bool", "BOOLEAN", 1, (0, 1)),
    "int8": _integer("int8", "INTEGER8", 8, signed=True),
    "int16": _integer("int16", "INTEGER16", 16, signed=True),
    "int32": _integer("int32", "INTEGER32", 32, signed=True),
    "int64": _integer("int64", "INTEGER64", 64, signed=True),
    "uint8": _integer("uint8", "UNSIGNED8", 8, signed=False),
    "uint16": _integer("uint16", "UNSIGNED16", 16, signed=False),
    "uint32": _integer("uint32", "UNSIGNED32", 32, signed=False),
    "uint64": _integer("uint64", "UNSIGNED64", 64, signed=False),
    "float32": PrimitiveDataType("float32", "REAL32", 32),
    "float64": PrimitiveDataType("float64", "REAL64", 64),
    "string": PrimitiveDataType("string", "VISIBLE_STRING", None, pdo_mappable=False),
    "domain": PrimitiveDataType("domain", "DOMAIN", None, pdo_mappable=False),
}

PRIMITIVE_TYPES: Final[Mapping[str, PrimitiveDataType]] = MappingProxyType(_PRIMITIVES)


def get_primitive(alias: str) -> PrimitiveDataType | None:
    """Return primitive metadata for an alias, or ``None`` for a custom type name."""
    return PRIMITIVE_TYPES.get(alias)


@dataclass(frozen=True, slots=True)
class EnumMember:
    """One symbolic integer member of a custom enum type."""

    name: str
    value: int


@dataclass(frozen=True, slots=True)
class CustomTypeDefinition:
    """An unresolved schema-v1 alias or enum declaration."""

    name: str
    base: str
    enum_members: tuple[EnumMember, ...] = ()

    @property
    def is_enum(self) -> bool:
        """Return whether this declaration adds enum semantics to its base type."""
        return bool(self.enum_members)
