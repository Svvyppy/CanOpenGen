"""Golden tests for deterministic Object Dictionary map output."""

from pathlib import Path

from canopengen.allocator import allocate_object_dictionary
from canopengen.odmap import format_object_dictionary_map
from canopengen.parser import parse_device
from canopengen.resolver import resolve_modules
from canopengen.type_resolver import resolve_module_graph_types

PROJECT_ROOT = Path(__file__).parents[2]


def test_pressure_sensor_map_matches_golden() -> None:
    """Unexpected public map-output changes fail a stable golden comparison."""
    device = parse_device(
        PROJECT_ROOT / "examples" / "definitions" / "Device" / "PressureSensor.yml"
    )
    graph = resolve_modules(device)
    resolved_types = resolve_module_graph_types(graph)
    dictionary = allocate_object_dictionary(graph.namespace, graph.objects)
    expected = (PROJECT_ROOT / "tests" / "golden" / "PressureSensor.map").read_text(
        encoding="utf-8"
    )

    assert format_object_dictionary_map(dictionary, resolved_types) == expected
