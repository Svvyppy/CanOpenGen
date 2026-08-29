"""Tests for schema-v1 YAML parsing into raw models."""

from pathlib import Path

import pytest

from canopengen.errors import (
    ParseError,
    SchemaValidationError,
    UnsupportedSchemaVersionError,
)
from canopengen.model import (
    Access,
    DeviceDefinition,
    ModuleDefinition,
    ObjectCategory,
    ObjectKind,
    PdoDirection,
)
from canopengen.parser import parse_definition, parse_device, parse_module

PROJECT_ROOT = Path(__file__).parents[2]
PRESSURE_SENSOR = PROJECT_ROOT / "Device" / "PressureSensor.yml"


def _write_yaml(tmp_path: Path, content: str, *, filename: str = "Definition.yml") -> Path:
    """Write one focused parser input in pytest's isolated directory."""
    path = tmp_path / filename
    path.write_text(content, encoding="utf-8")
    return path


def test_parse_complete_device() -> None:
    """The example covers modules, custom types, all object kinds, and PDOs."""
    device = parse_device(PRESSURE_SENSOR)

    assert device.name == "PressureSensor"
    assert device.schema_version == 1
    assert [module.name for module in device.imports] == [
        "CommonTypes",
        "FirmwareInfo",
        "Diagnostics",
    ]
    assert device.imports[2].parameters[0].name == "channel_count"
    assert device.imports[2].parameters[0].value == 4
    assert [type_definition.name for type_definition in device.types] == [
        "DeviceState",
        "Pressure",
        "RawPressure",
    ]


def test_parse_custom_alias_and_enum() -> None:
    """Alias bases remain unresolved while enum members become explicit models."""
    device = parse_device(PRESSURE_SENSOR)
    types = {type_definition.name: type_definition for type_definition in device.types}

    assert types["Pressure"].base == "RawPressure"
    assert not types["Pressure"].is_enum
    assert types["DeviceState"].is_enum
    assert [(member.name, member.value) for member in types["DeviceState"].enum_members] == [
        ("ACTIVE", 2),
        ("ERROR", 3),
        ("INIT", 0),
        ("READY", 1),
    ]


def test_parse_variable_and_manual_index() -> None:
    """Variables retain category, access, qualified name, and explicit index."""
    device = parse_device(PRESSURE_SENSOR)
    pressure = next(entry for entry in device.objects if entry.key == "pressure")

    assert pressure.kind is ObjectKind.VARIABLE
    assert pressure.qualified_name == "PressureSensor.pressure"
    assert pressure.category is ObjectCategory.TELEMETRY
    assert pressure.access is Access.READ_ONLY
    assert pressure.explicit_index == 0x2200


def test_parse_record_and_manual_subindex() -> None:
    """Record fields receive qualified names and retain explicit subindices."""
    device = parse_device(PRESSURE_SENSOR)
    calibration = next(entry for entry in device.objects if entry.key == "calibration")

    assert calibration.kind is ObjectKind.RECORD
    assert calibration.access is None
    assert [field.key for field in calibration.fields] == ["offset", "scale"]
    assert calibration.fields[0].qualified_name == "PressureSensor.calibration.offset"
    assert calibration.fields[0].explicit_subindex == 1
    assert calibration.fields[1].explicit_subindex is None


def test_parse_array() -> None:
    """Arrays retain their sequential element metadata as one unresolved object."""
    device = parse_device(PRESSURE_SENSOR)
    samples = next(entry for entry in device.objects if entry.key == "samples")

    assert samples.kind is ObjectKind.ARRAY
    assert samples.item_type == "uint16"
    assert samples.length == 8
    assert samples.access is Access.READ_ONLY


def test_parse_tpdo_and_rpdo() -> None:
    """PDO mapping order remains author-defined for later encoding."""
    device = parse_device(PRESSURE_SENSOR)

    assert [(pdo.direction, pdo.key, pdo.mapping) for pdo in device.pdos] == [
        (
            PdoDirection.TRANSMIT,
            "sensor_data",
            ("pressure", "state", "Diagnostics.supply_voltage"),
        ),
        (PdoDirection.RECEIVE, "commands", ("reset",)),
    ]


def test_module_filename_defines_namespace() -> None:
    """Module display text never replaces filename-based identity."""
    module = parse_module(PROJECT_ROOT / "Modules" / "FirmwareInfo.yml")

    assert module.name == "Firmware Information"
    assert module.namespace == "FirmwareInfo"
    assert module.imports[0].name == "CommonTypes"
    assert module.objects[0].qualified_name == "FirmwareInfo.firmware_version"


def test_parse_definition_returns_correct_variant() -> None:
    """The generic entry point discriminates devices from modules."""
    assert isinstance(parse_definition(PRESSURE_SENSOR), DeviceDefinition)
    assert isinstance(
        parse_definition(PROJECT_ROOT / "Modules" / "Diagnostics.yml"), ModuleDefinition
    )


def test_specific_parser_rejects_other_definition_kind() -> None:
    """Callers can require a Device or Module without unsafe casts."""
    with pytest.raises(SchemaValidationError, match="expected a Device"):
        parse_device(PROJECT_ROOT / "Modules" / "Diagnostics.yml")
    with pytest.raises(SchemaValidationError, match="expected a Module"):
        parse_module(PRESSURE_SENSOR)


@pytest.mark.parametrize("schema", [0, 2, "1"])
def test_unsupported_schema_version(tmp_path: Path, schema: object) -> None:
    """Unsupported schema versions produce a focused compatibility diagnostic."""
    path = _write_yaml(tmp_path, f"schema: {schema!r}\ndevice:\n  name: Test\n")

    with pytest.raises(UnsupportedSchemaVersionError, match="supported versions: 1"):
        parse_definition(path)


def test_missing_schema_version(tmp_path: Path) -> None:
    """A missing schema version suggests the exact schema-v1 declaration."""
    path = _write_yaml(tmp_path, "device:\n  name: Test\n")

    with pytest.raises(UnsupportedSchemaVersionError, match="add 'schema: 1'"):
        parse_definition(path)


def test_non_string_yaml_mapping_key_is_rejected(tmp_path: Path) -> None:
    """YAML-only key types fail cleanly before reaching the JSON Schema adapter."""
    path = _write_yaml(
        tmp_path,
        """schema: 1
device:
  name: Test
types:
  7:
    base: uint8
""",
    )

    with pytest.raises(SchemaValidationError, match="mapping keys must be strings; got 7"):
        parse_definition(path)


def test_malformed_yaml_reports_filename_and_line(tmp_path: Path) -> None:
    """YAML syntax errors retain actionable source location information."""
    path = _write_yaml(tmp_path, "schema: 1\ndevice: [\n")

    with pytest.raises(ParseError) as raised:
        parse_definition(path)

    assert str(path) in str(raised.value)
    assert f"{path}:3" in str(raised.value)


@pytest.mark.parametrize(
    ("field", "value"),
    [("category", "metrics"), ("access", "read")],
)
def test_invalid_object_enum_value(
    tmp_path: Path,
    field: str,
    value: str,
) -> None:
    """Invalid category/access spellings fail before model construction."""
    category = value if field == "category" else "telemetry"
    access = value if field == "access" else "ro"
    path = _write_yaml(
        tmp_path,
        f"""schema: 1
device:
  name: Test
objects:
  value:
    category: {category}
    type: uint8
    access: {access}
""",
    )

    with pytest.raises(SchemaValidationError, match=value):
        parse_device(path)


def test_invalid_record_shape(tmp_path: Path) -> None:
    """Records require at least one typed and accessible field."""
    path = _write_yaml(
        tmp_path,
        """schema: 1
device:
  name: Test
objects:
  settings:
    category: configuration
    type: record
""",
    )

    with pytest.raises(SchemaValidationError, match="fields"):
        parse_device(path)


def test_invalid_array_length(tmp_path: Path) -> None:
    """Array lengths outside the sequential subindex space are rejected."""
    path = _write_yaml(
        tmp_path,
        """schema: 1
device:
  name: Test
objects:
  samples:
    category: telemetry
    type: array
    item_type: uint8
    length: 256
    access: ro
""",
    )

    with pytest.raises(SchemaValidationError, match="maximum of 255"):
        parse_device(path)


def test_mapping_order_does_not_change_named_definition_order(tmp_path: Path) -> None:
    """Named YAML mappings normalize lexically for deterministic downstream behavior."""
    first = _write_yaml(
        tmp_path,
        """schema: 1
device:
  name: Test
objects:
  zed:
    category: telemetry
    type: uint8
    access: ro
  alpha:
    category: telemetry
    type: uint8
    access: ro
""",
        filename="First.yml",
    )
    second = _write_yaml(
        tmp_path,
        """schema: 1
device:
  name: Test
objects:
  alpha:
    access: ro
    type: uint8
    category: telemetry
  zed:
    access: ro
    category: telemetry
    type: uint8
""",
        filename="Second.yml",
    )

    assert parse_device(first).objects == parse_device(second).objects
    assert [entry.key for entry in parse_device(first).objects] == ["alpha", "zed"]
