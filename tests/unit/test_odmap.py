"""Golden tests for deterministic Object Dictionary map output."""

from pathlib import Path

from canopengen.allocator import allocate_object_dictionary
from canopengen.odmap import format_object_dictionary_map
from canopengen.parser import parse_device
from canopengen.type_resolver import resolve_definition_types

PROJECT_ROOT = Path(__file__).parents[2]


def test_pressure_sensor_map_matches_golden() -> None:
    """Unexpected public map-output changes fail a stable golden comparison."""
    device = parse_device(PROJECT_ROOT / "Device" / "PressureSensor.yml")
    resolved_types = resolve_definition_types(device)
    dictionary = allocate_object_dictionary(device.name, device.objects)
    expected = (PROJECT_ROOT / "tests" / "golden" / "PressureSensor.map").read_text(
        encoding="utf-8"
    )

    assert format_object_dictionary_map(dictionary, resolved_types) == expected
