"""Address-resolved models produced by the deterministic allocator."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from canopengen.model.object import Access, ObjectCategory, ObjectDefinition


class AddressSource(StrEnum):
    """How an index or subindex was selected."""

    EXPLICIT = "explicit"
    AUTOMATIC = "auto"
    RESERVED = "reserved"
    SEQUENTIAL = "sequential"


class SubObjectRole(StrEnum):
    """Semantic role of one allocated compound-object subentry."""

    COUNT = "count"
    RECORD_FIELD = "record-field"
    ARRAY_ELEMENT = "array-element"


@dataclass(frozen=True, slots=True)
class AllocatedSubObject:
    """One record/array subentry with a final CANopen subindex."""

    key: str
    qualified_name: str
    subindex: int
    type_name: str
    access: Access
    info: str | None
    address_source: AddressSource
    probe_distance: int
    role: SubObjectRole
    default_value: int | None = None


@dataclass(frozen=True, slots=True)
class AllocatedObject:
    """One raw object paired with its final deterministic address metadata."""

    definition: ObjectDefinition
    index: int
    address_source: AddressSource
    probe_distance: int
    subobjects: tuple[AllocatedSubObject, ...] = ()

    def subobject(self, subindex: int) -> AllocatedSubObject | None:
        """Return a compound subentry by numeric subindex."""
        return next((entry for entry in self.subobjects if entry.subindex == subindex), None)


@dataclass(frozen=True, slots=True)
class AllocatedObjectDictionary:
    """A deterministic allocation result for one set of qualified objects."""

    namespace: str
    objects: tuple[AllocatedObject, ...]

    def object_by_qualified_name(self, qualified_name: str) -> AllocatedObject | None:
        """Return an allocated object by semantic identity."""
        return next(
            (
                allocated
                for allocated in self.objects
                if allocated.definition.qualified_name == qualified_name
            ),
            None,
        )


@dataclass(frozen=True, slots=True)
class AddressDiagnostic:
    """Public CRC32 calculation details for the ``address`` command."""

    qualified_name: str
    category: ObjectCategory
    canonical_key: str
    crc32: int
    range_start: int
    range_end: int
    initial_slot: int
    initial_index: int
    final_index: int | None = None
    probe_distance: int | None = None
    address_source: AddressSource | None = None
