"""Tests for primitive datatype and raw object invariants."""

import pytest

from canopengen.model import (
    PRIMITIVE_TYPES,
    Access,
    ObjectCategory,
    ObjectDefinition,
    ObjectKind,
    SubObjectDefinition,
    get_primitive,
)


@pytest.mark.parametrize(
    ("alias", "canopen_name", "eds_data_type", "bit_width"),
    [
        ("bool", "BOOLEAN", 0x0001, 1),
        ("int16", "INTEGER16", 0x0003, 16),
        ("uint32", "UNSIGNED32", 0x0007, 32),
        ("float64", "REAL64", 0x0011, 64),
        ("string", "VISIBLE_STRING", 0x0009, None),
        ("domain", "DOMAIN", 0x000F, None),
    ],
)
def test_primitive_registry(
    alias: str,
    canopen_name: str,
    eds_data_type: int,
    bit_width: int | None,
) -> None:
    """Developer aliases map centrally to CANopen metadata."""
    primitive = get_primitive(alias)
    assert primitive is not None
    assert primitive.canopen_name == canopen_name
    assert primitive.eds_data_type == eds_data_type
    assert primitive.bit_width == bit_width


def test_primitive_integer_ranges() -> None:
    """Integer metadata provides exact ranges for future enum validation."""
    assert PRIMITIVE_TYPES["int8"].integer_range == (-128, 127)
    assert PRIMITIVE_TYPES["uint8"].integer_range == (0, 255)
    assert PRIMITIVE_TYPES["float32"].integer_range is None
    assert get_primitive("ApplicationAlias") is None


@pytest.mark.parametrize(
    ("category", "expected"),
    [
        (ObjectCategory.TELEMETRY, (0x2000, 0x27FF)),
        (ObjectCategory.COMMAND, (0x2800, 0x2FFF)),
        (ObjectCategory.CONFIGURATION, (0x3000, 0x37FF)),
        (ObjectCategory.DIAGNOSTIC, (0x3800, 0x3FFF)),
    ],
)
def test_category_ranges(category: ObjectCategory, expected: tuple[int, int]) -> None:
    """Schema-v1 categories expose their stable inclusive ranges."""
    assert category.index_range == expected


def test_object_kinds_are_explicit() -> None:
    """Raw objects hide YAML conditionals behind an explicit kind property."""
    variable = ObjectDefinition(
        key="value",
        qualified_name="Device.value",
        category=ObjectCategory.TELEMETRY,
        type_name="uint16",
        access=Access.READ_ONLY,
    )
    array = ObjectDefinition(
        key="samples",
        qualified_name="Device.samples",
        category=ObjectCategory.TELEMETRY,
        type_name="array",
        access=Access.READ_ONLY,
        item_type="uint16",
        length=8,
    )
    record = ObjectDefinition(
        key="settings",
        qualified_name="Device.settings",
        category=ObjectCategory.CONFIGURATION,
        type_name="record",
        access=None,
        fields=(
            SubObjectDefinition(
                key="gain",
                qualified_name="Device.settings.gain",
                type_name="float32",
                access=Access.READ_WRITE,
            ),
        ),
    )

    assert variable.kind is ObjectKind.VARIABLE
    assert array.kind is ObjectKind.ARRAY
    assert record.kind is ObjectKind.RECORD


def test_object_model_rejects_invalid_array_shape() -> None:
    """Direct raw-model construction cannot bypass structural invariants."""
    with pytest.raises(ValueError, match="item_type and length"):
        ObjectDefinition(
            key="samples",
            qualified_name="Device.samples",
            category=ObjectCategory.TELEMETRY,
            type_name="array",
            access=Access.READ_ONLY,
        )
