"""Tests for deterministic schema-v1 index and subindex allocation."""

from collections.abc import Iterable

import pytest

from canopengen.allocator import (
    allocate_object_dictionary,
    canonical_object_key,
    crc32_utf8,
    diagnose_address,
    initial_object_index,
    initial_record_subindex,
)
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
    AddressSource,
    ObjectCategory,
    ObjectDefinition,
    SubObjectDefinition,
    SubObjectRole,
)


def _variable(
    qualified_name: str,
    *,
    category: ObjectCategory = ObjectCategory.TELEMETRY,
    index: int | None = None,
) -> ObjectDefinition:
    """Build a small variable allocation input."""
    return ObjectDefinition(
        key=qualified_name.rsplit(".", maxsplit=1)[-1],
        qualified_name=qualified_name,
        category=category,
        type_name="uint8",
        access=Access.READ_ONLY,
        explicit_index=index,
    )


def _field(
    qualified_name: str,
    *,
    subindex: int | None = None,
) -> SubObjectDefinition:
    """Build a small record-field allocation input."""
    return SubObjectDefinition(
        key=qualified_name.rsplit(".", maxsplit=1)[-1],
        qualified_name=qualified_name,
        type_name="uint8",
        access=Access.READ_WRITE,
        explicit_subindex=subindex,
    )


def _record(fields: Iterable[SubObjectDefinition]) -> ObjectDefinition:
    """Build a record allocation input with a stable parent identity."""
    return ObjectDefinition(
        key="record",
        qualified_name="Device.record",
        category=ObjectCategory.CONFIGURATION,
        type_name="record",
        access=None,
        fields=tuple(fields),
    )


def test_crc32_public_vector() -> None:
    """Canonicalization and unsigned IEEE CRC-32 have a locked compatibility vector."""
    key = canonical_object_key(ObjectCategory.TELEMETRY, "PressureSensor.pressure")
    checksum, slot, index = initial_object_index(
        ObjectCategory.TELEMETRY, "PressureSensor.pressure"
    )

    assert key == "telemetry:PressureSensor.pressure"
    assert crc32_utf8(key) == 0xA66C98DF
    assert checksum == 0xA66C98DF
    assert slot == 223
    assert index == 0x20DF


@pytest.mark.parametrize("category", list(ObjectCategory))
def test_automatic_allocation_stays_in_each_category(category: ObjectCategory) -> None:
    """All four public category partitions are used exactly as modeled."""
    definition = _variable(f"Device.{category.value}", category=category)
    allocated = allocate_object_dictionary("Device", [definition]).objects[0]
    range_start, range_end = category.index_range

    assert range_start <= allocated.index <= range_end
    assert allocated.address_source is AddressSource.AUTOMATIC


def test_automatic_allocation_uses_crc32_initial_index() -> None:
    """An unoccupied hash slot is selected with zero probe distance."""
    definition = _variable("PressureSensor.pressure")
    allocated = allocate_object_dictionary("PressureSensor", [definition]).objects[0]

    assert allocated.index == 0x20DF
    assert allocated.probe_distance == 0


def test_explicit_index_has_priority_over_automatic_index() -> None:
    """All explicit addresses are reserved before any automatic object probes."""
    blocker = _variable("Device.blocker", index=0x20DF)
    automatic = _variable("PressureSensor.pressure")
    dictionary = allocate_object_dictionary("Device", [automatic, blocker])

    allocated_blocker = dictionary.object_by_qualified_name("Device.blocker")
    assert allocated_blocker is not None
    assert allocated_blocker.index == 0x20DF
    allocated = dictionary.object_by_qualified_name("PressureSensor.pressure")
    assert allocated is not None
    assert allocated.index == 0x20E0
    assert allocated.probe_distance == 1


def test_hash_collision_uses_lexical_order_and_linear_probing() -> None:
    """A fixed CRC32 collision vector resolves independently of input order."""
    first = _variable("Device.value_88")
    second = _variable("Device.value_400")
    assert initial_object_index(first.category, first.qualified_name)[1] == 496
    assert initial_object_index(second.category, second.qualified_name)[1] == 496

    dictionary = allocate_object_dictionary("Device", [first, second])
    lexical_first = dictionary.object_by_qualified_name("Device.value_400")
    lexical_second = dictionary.object_by_qualified_name("Device.value_88")
    assert lexical_first is not None
    assert lexical_second is not None
    assert (lexical_first.index, lexical_first.probe_distance) == (0x21F0, 0)
    assert (lexical_second.index, lexical_second.probe_distance) == (0x21F1, 1)


def test_index_probe_wraps_inside_category_range() -> None:
    """Linear probing wraps from a category's final slot to its first slot."""
    automatic = _variable("Device.wrap_663")
    assert initial_object_index(automatic.category, automatic.qualified_name)[2] == 0x27FF
    blocker = _variable("Device.blocker", index=0x27FF)

    allocated = allocate_object_dictionary("Device", [automatic, blocker]).object_by_qualified_name(
        automatic.qualified_name
    )
    assert allocated is not None
    assert allocated.index == 0x2000
    assert allocated.probe_distance == 1


def test_index_range_exhaustion() -> None:
    """Allocation fails only after every slot in the category is reserved."""
    explicit = [
        _variable(f"Device.explicit_{index:04X}", index=index) for index in range(0x2000, 0x2800)
    ]
    overflow = _variable("Device.overflow")

    with pytest.raises(IndexRangeExhaustedError, match=r"telemetry range.*is full"):
        allocate_object_dictionary("Device", [*explicit, overflow])


def test_explicit_index_collision() -> None:
    """Two manual indexes never silently probe or overwrite one another."""
    with pytest.raises(ExplicitIndexCollisionError, match="both use explicit index 0x2200"):
        allocate_object_dictionary(
            "Device",
            [_variable("Device.first", index=0x2200), _variable("Device.second", index=0x2200)],
        )


def test_explicit_index_must_match_category() -> None:
    """Schema-v1 manual indexes cannot escape their category partition."""
    with pytest.raises(ExplicitIndexOutOfRangeError, match="outside telemetry range"):
        allocate_object_dictionary("Device", [_variable("Device.value", index=0x3000)])


def test_duplicate_qualified_object_is_rejected() -> None:
    """Qualified names remain unique allocation identities."""
    with pytest.raises(DuplicateQualifiedNameError, match=r"Device\.value"):
        allocate_object_dictionary("Device", [_variable("Device.value"), _variable("Device.value")])


def test_yaml_object_order_does_not_change_allocations() -> None:
    """The complete allocation map is reproducible under input reordering."""
    objects = [
        _variable("Device.alpha"),
        _variable("Device.beta"),
        _variable("Device.gamma", category=ObjectCategory.DIAGNOSTIC),
    ]

    forward = allocate_object_dictionary("Device", objects)
    reverse = allocate_object_dictionary("Device", reversed(objects))
    assert forward == reverse


def test_same_configuration_is_reproducible() -> None:
    """Repeated allocations of the same complete configuration are identical."""
    objects = [_variable("Device.alpha"), _variable("Device.beta")]
    assert allocate_object_dictionary("Device", objects) == allocate_object_dictionary(
        "Device", objects
    )


def test_record_reserves_subindex_zero_and_hashes_fields() -> None:
    """Record count is reserved and automatic fields use the fixed CRC32 space."""
    record = _record(
        [
            _field("PressureSensor.calibration.offset"),
            _field("PressureSensor.calibration.scale"),
        ]
    )
    allocated = allocate_object_dictionary("Device", [record]).objects[0]
    count = allocated.subobject(0)
    offset = next(entry for entry in allocated.subobjects if entry.key == "offset")
    scale = next(entry for entry in allocated.subobjects if entry.key == "scale")

    assert count is not None
    assert count.role is SubObjectRole.COUNT
    assert count.default_value == 2
    assert initial_record_subindex(offset.qualified_name) == (0x74466827, 185, 186)
    assert initial_record_subindex(scale.qualified_name) == (0xA20B5F7B, 129, 130)
    assert (offset.subindex, scale.subindex) == (186, 130)


def test_explicit_record_subindex_has_priority() -> None:
    """A manual field subindex is reserved before automatic field probing."""
    automatic = _field("PressureSensor.calibration.offset")
    blocker = _field("Device.record.blocker", subindex=186)
    allocated = allocate_object_dictionary("Device", [_record([automatic, blocker])]).objects[0]
    offset = next(entry for entry in allocated.subobjects if entry.key == "offset")

    assert offset.subindex == 187
    assert offset.probe_distance == 1


def test_record_hash_collision_uses_linear_probing() -> None:
    """Record fields use lexical ordering for a fixed CRC32 collision vector."""
    first = _field("Device.record.field_16")
    second = _field("Device.record.field_36")
    assert initial_record_subindex(first.qualified_name)[2] == 216
    assert initial_record_subindex(second.qualified_name)[2] == 216

    allocated = allocate_object_dictionary("Device", [_record([second, first])]).objects[0]
    field_16 = next(entry for entry in allocated.subobjects if entry.key == "field_16")
    field_36 = next(entry for entry in allocated.subobjects if entry.key == "field_36")
    assert (field_16.subindex, field_16.probe_distance) == (216, 0)
    assert (field_36.subindex, field_36.probe_distance) == (217, 1)


def test_record_probe_wraps_to_subindex_one() -> None:
    """Record probing wraps from 254 to 1 while keeping 0 reserved."""
    automatic = _field("Device.record.wrap_450")
    assert initial_record_subindex(automatic.qualified_name)[2] == 254
    blocker = _field("Device.record.blocker", subindex=254)

    allocated = allocate_object_dictionary("Device", [_record([automatic, blocker])]).objects[0]
    wrapped = next(entry for entry in allocated.subobjects if entry.key == "wrap_450")
    assert wrapped.subindex == 1
    assert wrapped.probe_distance == 1


def test_record_subindex_exhaustion() -> None:
    """A record fails only when all 254 usable field subindices are occupied."""
    explicit = [
        _field(f"Device.record.explicit_{subindex}", subindex=subindex)
        for subindex in range(1, 255)
    ]
    overflow = _field("Device.record.overflow")

    with pytest.raises(RecordSubindexExhaustedError, match="exceeds 254 usable fields"):
        allocate_object_dictionary("Device", [_record([*explicit, overflow])])


def test_explicit_record_subindex_collision() -> None:
    """Two manual field subindices produce a focused collision diagnostic."""
    with pytest.raises(ExplicitSubindexCollisionError, match="subindex 0x01"):
        allocate_object_dictionary(
            "Device",
            [
                _record(
                    [
                        _field("Device.record.first", subindex=1),
                        _field("Device.record.second", subindex=1),
                    ]
                )
            ],
        )


@pytest.mark.parametrize("subindex", [0, 255])
def test_explicit_record_subindex_range(subindex: int) -> None:
    """Manual record fields are constrained to 1 through 254."""
    with pytest.raises(ExplicitSubindexOutOfRangeError, match="0x01-0xFE"):
        allocate_object_dictionary(
            "Device", [_record([_field("Device.record.value", subindex=subindex)])]
        )


def test_array_uses_reserved_count_and_sequential_subindices() -> None:
    """Array elements never use hashing and occupy 1 through length."""
    definition = ObjectDefinition(
        key="samples",
        qualified_name="Device.samples",
        category=ObjectCategory.TELEMETRY,
        type_name="array",
        access=Access.READ_ONLY,
        item_type="uint16",
        length=8,
    )
    allocated = allocate_object_dictionary("Device", [definition]).objects[0]

    count = allocated.subobject(0)
    assert count is not None
    assert count.default_value == 8
    assert [entry.subindex for entry in allocated.subobjects] == list(range(9))
    assert all(
        entry.address_source is AddressSource.SEQUENTIAL for entry in allocated.subobjects[1:]
    )


@pytest.mark.parametrize("length", [0, 256])
def test_array_length_validation(length: int) -> None:
    """Direct model inputs cannot exceed the sequential byte-sized count space."""
    definition = ObjectDefinition(
        key="samples",
        qualified_name="Device.samples",
        category=ObjectCategory.TELEMETRY,
        type_name="array",
        access=Access.READ_ONLY,
        item_type="uint8",
        length=length,
    )

    with pytest.raises(InvalidArrayLengthError, match="expected 1-255"):
        allocate_object_dictionary("Device", [definition])


def test_address_diagnostic_without_context() -> None:
    """The diagnostic exposes every public CRC32 input before probing."""
    diagnostic = diagnose_address("PressureSensor.pressure", ObjectCategory.TELEMETRY)

    assert diagnostic.canonical_key == "telemetry:PressureSensor.pressure"
    assert diagnostic.crc32 == 0xA66C98DF
    assert diagnostic.initial_slot == 223
    assert diagnostic.initial_index == 0x20DF
    assert diagnostic.final_index is None


def test_address_diagnostic_with_complete_context() -> None:
    """Complete context reports explicit override or post-probing final results."""
    definition = _variable("PressureSensor.pressure", index=0x2200)
    dictionary = allocate_object_dictionary("PressureSensor", [definition])
    diagnostic = diagnose_address(
        definition.qualified_name,
        definition.category,
        allocated=dictionary,
    )

    assert diagnostic.initial_index == 0x20DF
    assert diagnostic.final_index == 0x2200
    assert diagnostic.address_source is AddressSource.EXPLICIT
    assert diagnostic.probe_distance == 0


def test_address_diagnostic_rejects_missing_context_object() -> None:
    """A supplied configuration must actually contain the requested object."""
    dictionary = allocate_object_dictionary("Device", [_variable("Device.other")])

    with pytest.raises(UnknownAddressObjectError, match=r"Device\.value.*not present"):
        diagnose_address("Device.value", ObjectCategory.TELEMETRY, allocated=dictionary)
