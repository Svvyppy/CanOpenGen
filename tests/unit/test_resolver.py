"""Tests for recursive module and qualified-reference resolution."""

from pathlib import Path

import pytest

from canopengen.allocator import allocate_object_dictionary
from canopengen.errors import (
    AmbiguousDataTypeError,
    AmbiguousReferenceError,
    DuplicateModuleImportError,
    ModuleDependencyCycleError,
    ModuleParameterConflictError,
    UnknownModuleError,
    UnknownReferenceError,
)
from canopengen.parser import parse_device
from canopengen.resolver import resolve_modules, resolve_pdo_references
from canopengen.type_resolver import resolve_module_graph_types

PROJECT_ROOT = Path(__file__).parents[2]
PRESSURE_SENSOR = PROJECT_ROOT / "Device" / "PressureSensor.yml"


def _write_project(
    tmp_path: Path,
    device: str,
    modules: dict[str, str],
) -> Path:
    """Create a focused conventional Device/Modules project tree."""
    device_directory = tmp_path / "Device"
    modules_directory = tmp_path / "Modules"
    device_directory.mkdir()
    modules_directory.mkdir()
    device_path = device_directory / "Test.yml"
    device_path.write_text(device, encoding="utf-8")
    for name, content in modules.items():
        (modules_directory / f"{name}.yml").write_text(content, encoding="utf-8")
    return device_path


def _object_module(name: str, *, key: str = "status", type_name: str = "uint8") -> str:
    """Return one small reusable module with a diagnostic variable."""
    return f"""schema: 1
module:
  name: {name} Display
objects:
  {key}:
    category: diagnostic
    type: {type_name}
    access: ro
"""


def test_example_resolves_nested_modules_parameters_types_and_references() -> None:
    """The repository example exercises the complete Phase 4 graph."""
    device = parse_device(PRESSURE_SENSOR)
    graph = resolve_modules(device)

    assert [module.namespace for module in graph.modules] == [
        "CommonTypes",
        "Diagnostics",
        "FirmwareInfo",
    ]
    assert sum(module.namespace == "CommonTypes" for module in graph.modules) == 1
    diagnostics = graph.module("Diagnostics")
    assert diagnostics is not None
    assert diagnostics.definition.name == "Diagnostics"
    assert diagnostics.dependencies == ("CommonTypes",)
    assert diagnostics.parameter("channel_count") == 4

    resolved_types = resolve_module_graph_types(graph)
    firmware_type = resolved_types.object_type("FirmwareInfo.firmware_version")
    assert firmware_type is not None
    assert firmware_type.datatype is not None
    assert firmware_type.datatype.primitive.alias == "uint32"
    assert firmware_type.datatype.custom_type_name == "FirmwareVersion"
    assert resolved_types.custom_type("CommonTypes.FirmwareVersion") is not None

    pdos = resolve_pdo_references(graph)
    sensor_data = next(pdo for pdo in pdos if pdo.definition.key == "sensor_data")
    assert [reference.qualified_name for reference in sensor_data.mapping] == [
        "PressureSensor.pressure",
        "PressureSensor.state",
        "Diagnostics.supply_voltage",
    ]

    dictionary = allocate_object_dictionary(graph.namespace, graph.objects)
    assert dictionary.object_by_qualified_name("Diagnostics.supply_voltage") is not None
    assert dictionary.object_by_qualified_name("FirmwareInfo.firmware_version") is not None


def test_same_local_object_key_in_different_namespaces_coexists(tmp_path: Path) -> None:
    """Filename namespaces keep equal module-local keys distinct."""
    path = _write_project(
        tmp_path,
        """schema: 1
device:
  name: Test
modules: [Alpha, Beta]
""",
        {
            "Alpha": _object_module("Alpha"),
            "Beta": _object_module("Beta"),
        },
    )
    graph = resolve_modules(parse_device(path))
    dictionary = allocate_object_dictionary(graph.namespace, graph.objects)

    assert dictionary.object_by_qualified_name("Alpha.status") is not None
    assert dictionary.object_by_qualified_name("Beta.status") is not None


def test_local_reference_wins_over_imported_names(tmp_path: Path) -> None:
    """An owner's object key is selected before imported fallback candidates."""
    path = _write_project(
        tmp_path,
        """schema: 1
device:
  name: Test
modules: [Alpha, Beta]
objects:
  status:
    category: telemetry
    type: uint8
    access: ro
pdo:
  tpdo:
    local:
      mapping: [status]
""",
        {
            "Alpha": _object_module("Alpha"),
            "Beta": _object_module("Beta"),
        },
    )
    pdos = resolve_pdo_references(resolve_modules(parse_device(path)))

    assert pdos[0].mapping[0].qualified_name == "Test.status"


def test_module_reference_resolves_its_own_namespace_first(tmp_path: Path) -> None:
    """A module PDO prefers its local object over an equal dependency key."""
    path = _write_project(
        tmp_path,
        """schema: 1
device:
  name: Test
modules: [Consumer]
""",
        {
            "Base": _object_module("Base"),
            "Consumer": """schema: 1
module:
  name: Consumer
modules: [Base]
objects:
  status:
    category: diagnostic
    type: uint16
    access: ro
pdo:
  tpdo:
    local:
      mapping: [status]
""",
        },
    )
    pdos = resolve_pdo_references(resolve_modules(parse_device(path)))

    assert pdos[0].mapping[0].qualified_name == "Consumer.status"


def test_ambiguous_imported_reference_requires_qualification(tmp_path: Path) -> None:
    """Equal visible imported keys cannot be selected by an unqualified name."""
    path = _write_project(
        tmp_path,
        """schema: 1
device:
  name: Test
modules: [Alpha, Beta]
pdo:
  tpdo:
    ambiguous:
      mapping: [status]
""",
        {
            "Alpha": _object_module("Alpha"),
            "Beta": _object_module("Beta"),
        },
    )

    with pytest.raises(
        AmbiguousReferenceError,
        match=r"Alpha.status, Beta.status.*qualified reference",
    ):
        resolve_pdo_references(resolve_modules(parse_device(path)))


def test_unknown_reference_reports_owner_and_pdo(tmp_path: Path) -> None:
    """A missing mapping target carries useful source and PDO context."""
    path = _write_project(
        tmp_path,
        """schema: 1
device:
  name: Test
pdo:
  tpdo:
    missing:
      mapping: [absent]
""",
        {},
    )

    with pytest.raises(UnknownReferenceError, match=r"TPDO 'missing'.*'absent'.*'Test'"):
        resolve_pdo_references(resolve_modules(parse_device(path)))


def test_module_dependency_cycle_reports_complete_chain(tmp_path: Path) -> None:
    """Recursive loading reports every namespace in the dependency cycle."""
    path = _write_project(
        tmp_path,
        """schema: 1
device:
  name: Test
modules: [A]
""",
        {
            "A": "schema: 1\nmodule:\n  name: A\nmodules: [B]\n",
            "B": "schema: 1\nmodule:\n  name: B\nmodules: [C]\n",
            "C": "schema: 1\nmodule:\n  name: C\nmodules: [A]\n",
        },
    )

    with pytest.raises(ModuleDependencyCycleError, match=r"A -> B -> C -> A"):
        resolve_modules(parse_device(path))


def test_unknown_module_names_expected_source_path(tmp_path: Path) -> None:
    """Missing imports identify both the importer and conventional path."""
    path = _write_project(
        tmp_path,
        """schema: 1
device:
  name: Test
modules: [Missing]
""",
        {},
    )

    with pytest.raises(UnknownModuleError, match=r"Missing.*Modules/Missing.yml"):
        resolve_modules(parse_device(path))


def test_duplicate_direct_import_is_not_silently_deduplicated(tmp_path: Path) -> None:
    """Only equal transitive diamonds are deduplicated automatically."""
    path = _write_project(
        tmp_path,
        """schema: 1
device:
  name: Test
modules: [Shared, Shared]
""",
        {"Shared": "schema: 1\nmodule:\n  name: Shared\n"},
    )

    with pytest.raises(DuplicateModuleImportError, match="more than once"):
        resolve_modules(parse_device(path))


def test_conflicting_parameterized_diamond_fails(tmp_path: Path) -> None:
    """One module cannot silently acquire two configurations in the same graph."""
    path = _write_project(
        tmp_path,
        """schema: 1
device:
  name: Test
modules: [A, B]
""",
        {
            "A": """schema: 1
module:
  name: A
modules:
  - name: Shared
    params: {channel_count: 1}
""",
            "B": """schema: 1
module:
  name: B
modules:
  - name: Shared
    params: {channel_count: 2}
""",
            "Shared": "schema: 1\nmodule:\n  name: Shared\n",
        },
    )

    with pytest.raises(ModuleParameterConflictError, match=r"channel_count=2.*channel_count=1"):
        resolve_modules(parse_device(path))


def test_ambiguous_imported_datatype_requires_qualification(tmp_path: Path) -> None:
    """Scoped type lookup rejects equal imported local declaration names."""
    path = _write_project(
        tmp_path,
        """schema: 1
device:
  name: Test
modules: [Alpha, Beta]
objects:
  value:
    category: telemetry
    type: Reading
    access: ro
""",
        {
            "Alpha": "schema: 1\nmodule:\n  name: Alpha\ntypes:\n  Reading:\n    base: uint8\n",
            "Beta": "schema: 1\nmodule:\n  name: Beta\ntypes:\n  Reading:\n    base: uint16\n",
        },
    )
    graph = resolve_modules(parse_device(path))

    with pytest.raises(
        AmbiguousDataTypeError,
        match=r"Alpha.Reading, Beta.Reading.*qualified datatype",
    ):
        resolve_module_graph_types(graph)


def test_qualified_imported_datatype_resolves(tmp_path: Path) -> None:
    """An explicit module namespace selects one custom type deterministically."""
    path = _write_project(
        tmp_path,
        """schema: 1
device:
  name: Test
modules: [Alpha, Beta]
objects:
  value:
    category: telemetry
    type: Beta.Reading
    access: ro
""",
        {
            "Alpha": "schema: 1\nmodule:\n  name: Alpha\ntypes:\n  Reading:\n    base: uint8\n",
            "Beta": "schema: 1\nmodule:\n  name: Beta\ntypes:\n  Reading:\n    base: uint16\n",
        },
    )
    resolved = resolve_module_graph_types(resolve_modules(parse_device(path)))
    datatype = resolved.object_type("Test.value")

    assert datatype is not None
    assert datatype.datatype is not None
    assert datatype.datatype.primitive.alias == "uint16"
    assert datatype.datatype.custom_type_name == "Beta.Reading"
