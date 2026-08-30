"""Tests for deterministic complete-device Markdown generation."""

from pathlib import Path

from canopengen.allocator import allocate_object_dictionary
from canopengen.generators import generate_markdown
from canopengen.parser import parse_device
from canopengen.resolver import resolve_modules, resolve_pdo_references
from canopengen.type_resolver import resolve_module_graph_types

PROJECT_ROOT = Path(__file__).parents[2]


def _pressure_sensor_markdown() -> str:
    """Generate the complete example document from resolved Phase 5 IR."""
    device = parse_device(
        PROJECT_ROOT / "examples" / "definitions" / "Device" / "PressureSensor.yml"
    )
    graph = resolve_modules(device)
    return generate_markdown(
        device,
        graph,
        allocate_object_dictionary(graph.namespace, graph.objects),
        resolve_module_graph_types(graph),
        resolve_pdo_references(graph),
    )


def test_pressure_sensor_markdown_matches_golden() -> None:
    """Public Markdown changes require a deliberate golden-file update."""
    expected = (PROJECT_ROOT / "tests" / "golden" / "PressureSensor.md").read_text(encoding="utf-8")

    assert _pressure_sensor_markdown() == expected


def test_markdown_includes_complete_object_and_type_metadata() -> None:
    """Every rich Phase 6 document section derives from the resolved model."""
    document = _pressure_sensor_markdown()

    assert "| Qualified name | `FirmwareInfo.firmware_version` |" in document
    assert "| `0x82` | `scale` | `PressureSensor.calibration.scale` | `float32`" in document
    assert "| `0x08` | `samples[8]` | `PressureSensor.samples[8]` | `uint16`" in document
    assert "### `PressureSensor.DeviceState`" in document
    assert "| `ERROR` | `3` |" in document
    assert "Declared scalar payload: 56 bits." in document
    assert "| `Diagnostics.supply_voltage` | `Diagnostics.supply_voltage` | 16 bits |" in document
