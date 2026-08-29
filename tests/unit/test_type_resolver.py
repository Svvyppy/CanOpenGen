"""Tests for recursive custom datatype resolution."""

from pathlib import Path

import pytest

from canopengen.errors import (
    AliasCycleError,
    EnumValueOutOfRangeError,
    InvalidEnumBaseError,
    ReservedTypeNameError,
    UnknownDataTypeError,
)
from canopengen.model import (
    Access,
    CustomTypeDefinition,
    DeviceDefinition,
    EnumMember,
    ObjectCategory,
    ObjectDefinition,
    SubObjectDefinition,
)
from canopengen.type_resolver import resolve_definition_types

SOURCE_PATH = Path("Device/Test.yml")


def _variable(type_name: str, *, key: str = "value") -> ObjectDefinition:
    """Build a small variable type-resolution input."""
    return ObjectDefinition(
        key=key,
        qualified_name=f"Test.{key}",
        category=ObjectCategory.TELEMETRY,
        type_name=type_name,
        access=Access.READ_ONLY,
    )


def _device(
    *,
    types: tuple[CustomTypeDefinition, ...] = (),
    objects: tuple[ObjectDefinition, ...] = (),
) -> DeviceDefinition:
    """Build one raw device with explicit test declarations."""
    return DeviceDefinition(
        schema_version=1,
        name="Test",
        source_path=SOURCE_PATH,
        types=types,
        objects=objects,
    )


def test_primitive_reference() -> None:
    """Primitive object references resolve without a custom type name."""
    resolved = resolve_definition_types(_device(objects=(_variable("uint16"),)))
    datatype = resolved.objects[0].datatype

    assert datatype is not None
    assert datatype.primitive.alias == "uint16"
    assert datatype.primitive.canopen_name == "UNSIGNED16"
    assert datatype.custom_type_name is None
    assert datatype.alias_chain == ("uint16",)


def test_alias_resolution() -> None:
    """A direct alias lowers to its standard CANopen primitive."""
    alias = CustomTypeDefinition(name="Pressure", base="uint32")
    resolved = resolve_definition_types(_device(types=(alias,), objects=(_variable("Pressure"),)))
    datatype = resolved.objects[0].datatype

    assert datatype is not None
    assert datatype.primitive.alias == "uint32"
    assert datatype.custom_type_name == "Pressure"
    assert datatype.alias_chain == ("Pressure", "uint32")


def test_nested_alias_resolution() -> None:
    """Alias inheritance recursively records the complete lowering chain."""
    resolved = resolve_definition_types(
        _device(
            types=(
                CustomTypeDefinition(name="RawPressure", base="uint32"),
                CustomTypeDefinition(name="Pressure", base="RawPressure"),
            ),
            objects=(_variable("Pressure"),),
        )
    )
    datatype = resolved.objects[0].datatype

    assert datatype is not None
    assert datatype.primitive.alias == "uint32"
    assert datatype.alias_chain == ("Pressure", "RawPressure", "uint32")


def test_enum_resolution_and_numeric_order() -> None:
    """Enums lower to integer storage while retaining sorted symbolic semantics."""
    state = CustomTypeDefinition(
        name="State",
        base="uint8",
        enum_members=(
            EnumMember("ERROR", 3),
            EnumMember("READY", 1),
            EnumMember("INIT", 0),
        ),
    )
    resolved = resolve_definition_types(_device(types=(state,), objects=(_variable("State"),)))
    datatype = resolved.objects[0].datatype

    assert datatype is not None
    assert datatype.primitive.alias == "uint8"
    assert [(member.value, member.name) for member in datatype.enum_members] == [
        (0, "INIT"),
        (1, "READY"),
        (3, "ERROR"),
    ]


def test_enum_base_may_be_nested_alias() -> None:
    """An enum base may traverse aliases before reaching integer storage."""
    resolved = resolve_definition_types(
        _device(
            types=(
                CustomTypeDefinition(name="StateStorage", base="uint16"),
                CustomTypeDefinition(
                    name="State",
                    base="StateStorage",
                    enum_members=(EnumMember("READY", 1),),
                ),
            )
        )
    )
    state = resolved.custom_type("State")

    assert state is not None
    assert state.primitive.alias == "uint16"
    assert state.alias_chain == ("State", "StateStorage", "uint16")
    assert state.is_enum


def test_alias_of_enum_inherits_semantics() -> None:
    """An alias of an enum retains the underlying enum member meanings."""
    resolved = resolve_definition_types(
        _device(
            types=(
                CustomTypeDefinition(
                    name="State",
                    base="uint8",
                    enum_members=(EnumMember("READY", 1),),
                ),
                CustomTypeDefinition(name="CurrentState", base="State"),
            ),
            objects=(_variable("CurrentState"),),
        )
    )
    datatype = resolved.objects[0].datatype

    assert datatype is not None
    assert datatype.alias_chain == ("CurrentState", "State", "uint8")
    assert datatype.enum_members == (EnumMember("READY", 1),)


def test_alias_cycle_reports_complete_chain() -> None:
    """Recursive aliases fail with the exact dependency cycle."""
    device = _device(
        types=(
            CustomTypeDefinition(name="A", base="B"),
            CustomTypeDefinition(name="B", base="C"),
            CustomTypeDefinition(name="C", base="A"),
        )
    )

    with pytest.raises(AliasCycleError, match=r"A -> B -> C -> A"):
        resolve_definition_types(device)


def test_unknown_alias_base() -> None:
    """Unknown custom bases identify both declaration and missing name."""
    device = _device(types=(CustomTypeDefinition(name="Pressure", base="Missing"),))

    with pytest.raises(
        UnknownDataTypeError,
        match=r"custom type 'Pressure' has unknown base 'Missing'",
    ):
        resolve_definition_types(device)


def test_unknown_object_type() -> None:
    """Unknown object references include their qualified object name."""
    device = _device(objects=(_variable("Missing", key="pressure"),))

    with pytest.raises(
        UnknownDataTypeError,
        match=r"object 'Test\.pressure'.*unknown datatype 'Missing'",
    ):
        resolve_definition_types(device)


@pytest.mark.parametrize(
    ("base", "value"),
    [("uint8", -1), ("uint8", 256), ("int8", -129), ("int8", 128)],
)
def test_enum_range_validation(base: str, value: int) -> None:
    """Enum values must fit the exact resolved signed/unsigned storage range."""
    device = _device(
        types=(
            CustomTypeDefinition(
                name="State",
                base=base,
                enum_members=(EnumMember("INVALID", value),),
            ),
        )
    )

    with pytest.raises(EnumValueOutOfRangeError, match=rf"value {value} is outside {base} range"):
        resolve_definition_types(device)


@pytest.mark.parametrize("base", ["bool", "float32", "float64", "string", "domain"])
def test_enum_requires_integer_primitive(base: str) -> None:
    """Boolean, real, string, and domain primitives cannot store schema-v1 enums."""
    device = _device(
        types=(
            CustomTypeDefinition(
                name="State",
                base=base,
                enum_members=(EnumMember("READY", 1),),
            ),
        )
    )

    with pytest.raises(InvalidEnumBaseError, match=rf"non-integer primitive '{base}'"):
        resolve_definition_types(device)


@pytest.mark.parametrize("name", ["uint8", "record", "array"])
def test_custom_type_cannot_shadow_reserved_name(name: str) -> None:
    """Primitive and structural type spellings remain unambiguous."""
    device = _device(types=(CustomTypeDefinition(name=name, base="uint16"),))

    with pytest.raises(ReservedTypeNameError, match=rf"custom type '{name}'.*reserved"):
        resolve_definition_types(device)


def test_record_fields_and_array_items_are_resolved() -> None:
    """Compound child types lower through the same resolver as variables."""
    alias = CustomTypeDefinition(name="Reading", base="int16")
    record = ObjectDefinition(
        key="settings",
        qualified_name="Test.settings",
        category=ObjectCategory.CONFIGURATION,
        type_name="record",
        access=None,
        fields=(
            SubObjectDefinition(
                key="offset",
                qualified_name="Test.settings.offset",
                type_name="Reading",
                access=Access.READ_WRITE,
            ),
        ),
    )
    array = ObjectDefinition(
        key="samples",
        qualified_name="Test.samples",
        category=ObjectCategory.TELEMETRY,
        type_name="array",
        access=Access.READ_ONLY,
        item_type="Reading",
        length=4,
    )

    resolved = resolve_definition_types(_device(types=(alias,), objects=(record, array)))
    record_type = resolved.object_type("Test.settings")
    array_type = resolved.object_type("Test.samples")
    assert record_type is not None
    assert array_type is not None
    assert record_type.fields[0].datatype.primitive.alias == "int16"
    assert record_type.fields[0].datatype.custom_type_name == "Reading"
    assert array_type.item_datatype is not None
    assert array_type.item_datatype.primitive.alias == "int16"
