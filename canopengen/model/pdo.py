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
