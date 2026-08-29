"""Deterministic schema-v1 CANopen index and subindex allocation."""

from __future__ import annotations

import zlib
from collections.abc import Iterable

from canopengen.errors import (
    DuplicateQualifiedNameError,
    ExplicitIndexCollisionError,
    ExplicitIndexOutOfRangeError,
    ExplicitSubindexCollisionError,
    ExplicitSubindexOutOfRangeError,
    IndexRangeExhaustedError,
    InvalidArrayLengthError,
    RecordSubindexExhaustedError,
    UnknownAddressObjectError,
)
from canopengen.model import (
    Access,
    AddressDiagnostic,
    AddressSource,
    AllocatedObject,
    AllocatedObjectDictionary,
    AllocatedSubObject,
    ObjectCategory,
    ObjectDefinition,
    ObjectKind,
    SubObjectRole,
)

RECORD_SUBINDEX_START = 1
RECORD_SUBINDEX_END = 254
ARRAY_LENGTH_MIN = 1
ARRAY_LENGTH_MAX = 255


def crc32_utf8(canonical_key: str) -> int:
    """Calculate unsigned IEEE CRC-32 over the UTF-8 canonical key.

    @param canonical_key Exact compatibility key.
    @return Unsigned 32-bit IEEE CRC-32.
    """
    return zlib.crc32(canonical_key.encode("utf-8")) & 0xFFFFFFFF


def canonical_object_key(category: ObjectCategory, qualified_name: str) -> str:
    """Return the schema-v1 object allocation key.

    The exact form ``<category>:<qualified-name>`` is public compatibility behavior.
    """
    return f"{category.value}:{qualified_name}"


def initial_object_index(category: ObjectCategory, qualified_name: str) -> tuple[int, int, int]:
    """Return ``(crc32, zero-based slot, CANopen index)`` before probing."""
    range_start, range_end = category.index_range
    range_size = range_end - range_start + 1
    checksum = crc32_utf8(canonical_object_key(category, qualified_name))
    slot = checksum % range_size
    return checksum, slot, range_start + slot


def initial_record_subindex(qualified_name: str) -> tuple[int, int, int]:
    """Return ``(crc32, zero-based slot, subindex)`` before record probing."""
    range_size = RECORD_SUBINDEX_END - RECORD_SUBINDEX_START + 1
    checksum = crc32_utf8(qualified_name)
    slot = checksum % range_size
    return checksum, slot, RECORD_SUBINDEX_START + slot


def _require_unique_qualified_names(objects: tuple[ObjectDefinition, ...]) -> None:
    """Reject duplicate object and record-field identities before allocation."""
    qualified_names: set[str] = set()
    for definition in objects:
        if definition.qualified_name in qualified_names:
            raise DuplicateQualifiedNameError(
                f"duplicate qualified object '{definition.qualified_name}'; rename one object"
            )
        qualified_names.add(definition.qualified_name)

        for field in definition.fields:
            if field.qualified_name in qualified_names:
                raise DuplicateQualifiedNameError(
                    f"duplicate qualified record field '{field.qualified_name}'; rename one field"
                )
            qualified_names.add(field.qualified_name)


def _allocate_record_subobjects(definition: ObjectDefinition) -> tuple[AllocatedSubObject, ...]:
    """Allocate record fields with explicit priority and CRC32 linear probing."""
    occupied: dict[int, str] = {}
    assigned: dict[str, tuple[int, AddressSource, int]] = {}

    for field in definition.fields:
        subindex = field.explicit_subindex
        if subindex is None:
            continue
        if not RECORD_SUBINDEX_START <= subindex <= RECORD_SUBINDEX_END:
            raise ExplicitSubindexOutOfRangeError(
                f"record field '{field.qualified_name}' uses subindex 0x{subindex:02X}; "
                "record fields must use 0x01-0xFE"
            )
        existing = occupied.get(subindex)
        if existing is not None:
            raise ExplicitSubindexCollisionError(
                f"record fields '{existing}' and '{field.qualified_name}' both use explicit "
                f"subindex 0x{subindex:02X}"
            )
        occupied[subindex] = field.qualified_name
        assigned[field.qualified_name] = (subindex, AddressSource.EXPLICIT, 0)

    range_size = RECORD_SUBINDEX_END - RECORD_SUBINDEX_START + 1
    automatic_fields = sorted(
        (field for field in definition.fields if field.explicit_subindex is None),
        key=lambda field: field.qualified_name,
    )
    for field in automatic_fields:
        _, initial_slot, _ = initial_record_subindex(field.qualified_name)
        for probe in range(range_size):
            slot = (initial_slot + probe) % range_size
            subindex = RECORD_SUBINDEX_START + slot
            if subindex not in occupied:
                occupied[subindex] = field.qualified_name
                assigned[field.qualified_name] = (subindex, AddressSource.AUTOMATIC, probe)
                break
        else:
            raise RecordSubindexExhaustedError(
                f"record '{definition.qualified_name}' exceeds 254 usable fields; "
                f"cannot allocate '{field.qualified_name}'"
            )

    count = AllocatedSubObject(
        key=definition.key,
        qualified_name=definition.qualified_name,
        subindex=0,
        type_name="uint8",
        access=Access.READ_ONLY,
        info=definition.info,
        address_source=AddressSource.RESERVED,
        probe_distance=0,
        role=SubObjectRole.COUNT,
        default_value=len(definition.fields),
    )
    fields = tuple(
        AllocatedSubObject(
            key=field.key,
            qualified_name=field.qualified_name,
            subindex=assigned[field.qualified_name][0],
            type_name=field.type_name,
            access=field.access,
            info=field.info,
            address_source=assigned[field.qualified_name][1],
            probe_distance=assigned[field.qualified_name][2],
            role=SubObjectRole.RECORD_FIELD,
        )
        for field in sorted(
            definition.fields,
            key=lambda item: (assigned[item.qualified_name][0], item.qualified_name),
        )
    )
    return (count, *fields)


def _allocate_array_subobjects(definition: ObjectDefinition) -> tuple[AllocatedSubObject, ...]:
    """Allocate standard sequential array element subindices."""
    length = definition.length
    if length is None or not ARRAY_LENGTH_MIN <= length <= ARRAY_LENGTH_MAX:
        raise InvalidArrayLengthError(
            f"array '{definition.qualified_name}' length {length!r} is invalid; "
            "expected 1-255 elements"
        )
    if definition.item_type is None or definition.access is None:
        raise InvalidArrayLengthError(
            f"array '{definition.qualified_name}' is missing item_type or access metadata"
        )

    count = AllocatedSubObject(
        key=definition.key,
        qualified_name=definition.qualified_name,
        subindex=0,
        type_name="uint8",
        access=Access.READ_ONLY,
        info=definition.info,
        address_source=AddressSource.RESERVED,
        probe_distance=0,
        role=SubObjectRole.COUNT,
        default_value=length,
    )
    elements = tuple(
        AllocatedSubObject(
            key=f"{definition.key}[{element}]",
            qualified_name=f"{definition.qualified_name}[{element}]",
            subindex=element,
            type_name=definition.item_type,
            access=definition.access,
            info=None,
            address_source=AddressSource.SEQUENTIAL,
            probe_distance=0,
            role=SubObjectRole.ARRAY_ELEMENT,
        )
        for element in range(1, length + 1)
    )
    return (count, *elements)


def _allocate_subobjects(definition: ObjectDefinition) -> tuple[AllocatedSubObject, ...]:
    """Dispatch compound subindex allocation by explicit object kind."""
    if definition.kind is ObjectKind.RECORD:
        return _allocate_record_subobjects(definition)
    if definition.kind is ObjectKind.ARRAY:
        return _allocate_array_subobjects(definition)
    return ()


def allocate_object_dictionary(
    namespace: str,
    objects: Iterable[ObjectDefinition],
) -> AllocatedObjectDictionary:
    """Allocate final indexes and compound subindices deterministically.

    Explicit indexes are validated and reserved before automatic objects. Automatic
    objects are sorted lexically by qualified name within each category, hashed using
    IEEE CRC-32, and assigned with wraparound linear probing.

    @param namespace Owner namespace for the returned dictionary.
    @param objects Complete application-object set to allocate.
    @return Immutable allocated Object Dictionary.
    @raises AllocationError For duplicates, invalid explicit addresses, or exhaustion.
    """
    definitions = tuple(objects)
    _require_unique_qualified_names(definitions)
    assignments: dict[str, tuple[int, AddressSource, int]] = {}

    for category in ObjectCategory:
        range_start, range_end = category.index_range
        occupied: dict[int, str] = {}
        category_objects = tuple(
            definition for definition in definitions if definition.category is category
        )

        for definition in category_objects:
            index = definition.explicit_index
            if index is None:
                continue
            if not range_start <= index <= range_end:
                raise ExplicitIndexOutOfRangeError(
                    f"object '{definition.qualified_name}' uses index 0x{index:04X}, outside "
                    f"{category.value} range 0x{range_start:04X}-0x{range_end:04X}"
                )
            existing = occupied.get(index)
            if existing is not None:
                raise ExplicitIndexCollisionError(
                    f"objects '{existing}' and '{definition.qualified_name}' both use explicit "
                    f"index 0x{index:04X}"
                )
            occupied[index] = definition.qualified_name
            assignments[definition.qualified_name] = (index, AddressSource.EXPLICIT, 0)

        range_size = range_end - range_start + 1
        automatic_objects = sorted(
            (definition for definition in category_objects if definition.explicit_index is None),
            key=lambda definition: definition.qualified_name,
        )
        for definition in automatic_objects:
            _, initial_slot, _ = initial_object_index(category, definition.qualified_name)
            for probe in range(range_size):
                slot = (initial_slot + probe) % range_size
                index = range_start + slot
                if index not in occupied:
                    occupied[index] = definition.qualified_name
                    assignments[definition.qualified_name] = (
                        index,
                        AddressSource.AUTOMATIC,
                        probe,
                    )
                    break
            else:
                raise IndexRangeExhaustedError(
                    f"{category.value} range 0x{range_start:04X}-0x{range_end:04X} is full; "
                    f"cannot allocate '{definition.qualified_name}'"
                )

    allocated = tuple(
        AllocatedObject(
            definition=definition,
            index=assignments[definition.qualified_name][0],
            address_source=assignments[definition.qualified_name][1],
            probe_distance=assignments[definition.qualified_name][2],
            subobjects=_allocate_subobjects(definition),
        )
        for definition in sorted(
            definitions,
            key=lambda item: (assignments[item.qualified_name][0], item.qualified_name),
        )
    )
    return AllocatedObjectDictionary(namespace=namespace, objects=allocated)


def diagnose_address(
    qualified_name: str,
    category: ObjectCategory,
    *,
    allocated: AllocatedObjectDictionary | None = None,
) -> AddressDiagnostic:
    """Return reproducible CRC32 and optional post-probing address details."""
    checksum, slot, initial_index = initial_object_index(category, qualified_name)
    range_start, range_end = category.index_range
    if allocated is None:
        return AddressDiagnostic(
            qualified_name=qualified_name,
            category=category,
            canonical_key=canonical_object_key(category, qualified_name),
            crc32=checksum,
            range_start=range_start,
            range_end=range_end,
            initial_slot=slot,
            initial_index=initial_index,
        )

    match = allocated.object_by_qualified_name(qualified_name)
    if match is None:
        raise UnknownAddressObjectError(
            f"object '{qualified_name}' is not present in allocation context "
            f"'{allocated.namespace}'"
        )
    if match.definition.category is not category:
        raise UnknownAddressObjectError(
            f"object '{qualified_name}' belongs to category '{match.definition.category.value}', "
            f"not '{category.value}'"
        )
    return AddressDiagnostic(
        qualified_name=qualified_name,
        category=category,
        canonical_key=canonical_object_key(category, qualified_name),
        crc32=checksum,
        range_start=range_start,
        range_end=range_end,
        initial_slot=slot,
        initial_index=initial_index,
        final_index=match.index,
        probe_distance=match.probe_distance,
        address_source=match.address_source,
    )
