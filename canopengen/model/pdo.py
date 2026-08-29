"""Unresolved PDO mapping declarations."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class PdoDirection(StrEnum):
    """Supported schema-v1 process data directions."""

    TRANSMIT = "tpdo"
    RECEIVE = "rpdo"


@dataclass(frozen=True, slots=True)
class PdoDefinition:
    """A named PDO whose symbolic entries are resolved in a later phase."""

    key: str
    owner_namespace: str
    direction: PdoDirection
    mapping: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ResolvedObjectReference:
    """One symbolic PDO entry paired with its deterministic qualified target."""

    declared_name: str
    qualified_name: str


@dataclass(frozen=True, slots=True)
class ResolvedPdoDefinition:
    """A raw PDO declaration whose object references are no longer ambiguous."""

    definition: PdoDefinition
    mapping: tuple[ResolvedObjectReference, ...]


@dataclass(frozen=True, slots=True)
class PdoMappingEntry:
    """One validated classic-CANopen mapping value and its source metadata."""

    reference: ResolvedObjectReference
    index: int
    subindex: int
    datatype_alias: str
    bit_width: int

    @property
    def encoding(self) -> int:
        """Return the standard ``index:subindex:length`` 32-bit mapping value."""
        return (self.index << 16) | (self.subindex << 8) | self.bit_width


@dataclass(frozen=True, slots=True)
class ResolvedPdoMapping:
    """One PDO after object addresses, storage type, and payload budget validation."""

    definition: PdoDefinition
    entries: tuple[PdoMappingEntry, ...]

    @property
    def total_bits(self) -> int:
        """Return the total classic-CANopen PDO payload length."""
        return sum(entry.bit_width for entry in self.entries)
