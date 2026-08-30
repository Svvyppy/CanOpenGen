"""Tests for typed C++ Object Dictionary symbol generation."""

from pathlib import Path

from canopengen.allocator import allocate_object_dictionary
from canopengen.generators import generate_cpp_symbols
from canopengen.parser import parse_device
from canopengen.resolver import resolve_modules
from canopengen.type_resolver import resolve_module_graph_types

PROJECT_ROOT = Path(__file__).parents[2]
PRESSURE_SENSOR = PROJECT_ROOT / "examples" / "definitions" / "Device" / "PressureSensor.yml"


def test_cpp_symbols_expose_typed_variable_record_array_and_enum_metadata() -> None:
    """One resolved IR produces symbolic access metadata for every object shape."""
    device = parse_device(PRESSURE_SENSOR)
    graph = resolve_modules(device)
    resolved_types = resolve_module_graph_types(graph)
    dictionary = allocate_object_dictionary(graph.namespace, graph.objects)

    generated = generate_cpp_symbols("PressureSensor", dictionary, resolved_types)

    assert "namespace PressureSensor {" in generated
    assert "enum class DeviceState : std::uint8_t" in generated
    assert "struct Pressure {" in generated
    assert "using Type = std::uint32_t;" in generated
    assert "static constexpr std::uint16_t index = 0x2200;" in generated
    assert "namespace Calibration {" in generated
    assert "struct Offset {" in generated
    assert "namespace Samples {" in generated
    assert "inline constexpr Item1 item1{};" in generated
    assert "namespace Diagnostics {" in generated
    assert "void SetValue(TObjectDictionary& dictionary" in generated
    assert "typename TObject::Type GetValue(TObjectDictionary& dictionary, TObject)" in generated
