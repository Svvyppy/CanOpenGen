"""Tests for deterministic Eds2Od-compatible EDS generation."""

from pathlib import Path

from canopengen.allocator import allocate_object_dictionary
from canopengen.generators import generate_eds
from canopengen.parser import parse_device
from canopengen.resolver import resolve_modules
from canopengen.type_resolver import resolve_module_graph_types

PROJECT_ROOT = Path(__file__).parents[2]


def _pressure_sensor_eds() -> str:
    """Generate the repository example from fully resolved Phase 4 IR."""
    device = parse_device(
        PROJECT_ROOT / "examples" / "definitions" / "Device" / "PressureSensor.yml"
    )
    graph = resolve_modules(device)
    resolved_types = resolve_module_graph_types(graph)
    dictionary = allocate_object_dictionary(graph.namespace, graph.objects)
    return generate_eds(device.name, dictionary, resolved_types)


def test_pressure_sensor_eds_matches_golden() -> None:
    """Public EDS output changes require an intentional golden update."""
    expected = (PROJECT_ROOT / "tests" / "golden" / "PressureSensor.eds").read_text(
        encoding="utf-8"
    )

    assert _pressure_sensor_eds() == expected


def test_eds_lowers_custom_types_and_renders_compound_objects() -> None:
    """Aliases/enums lower to CiA codes and containers include all leaf entries."""
    eds = _pressure_sensor_eds()

    assert "[2200]\nParameterName=PressureSensor.pressure\nObjectType=0x7\nDataType=0x0007" in eds
    assert "[24E4]\nParameterName=PressureSensor.state\nObjectType=0x7\nDataType=0x0005" in eds
    assert "[3129]\nParameterName=PressureSensor.calibration\nObjectType=0x9\nSubNumber=3" in eds
    assert "[3129sub0]\nParameterName=Number of Entries\nObjectType=0x7\nDataType=0x0005" in eds
    assert "[3129sub1]\nParameterName=offset\nObjectType=0x7\nDataType=0x0004" in eds
    assert "[20EB]\nParameterName=PressureSensor.samples\nObjectType=0x8\nSubNumber=9" in eds
    assert "[20EBsub8]\nParameterName=samples[8]\nObjectType=0x7\nDataType=0x0006" in eds
    assert (
        "[3DA3]\nParameterName=FirmwareInfo.firmware_version\nObjectType=0x7\nDataType=0x0007"
        in eds
    )
