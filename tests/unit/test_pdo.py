"""Tests for classic CANopen PDO mapping encoding."""

from pathlib import Path

import pytest

from canopengen.allocator import allocate_object_dictionary
from canopengen.errors import PdoValidationError
from canopengen.parser import parse_device
from canopengen.pdo import resolve_pdo_mappings
from canopengen.resolver import resolve_modules, resolve_pdo_references
from canopengen.type_resolver import resolve_module_graph_types

PROJECT_ROOT = Path(__file__).parents[2]


def test_pdo_entries_encode_final_addresses_and_exact_payload() -> None:
    """Mappings use allocated index/subindex plus resolved primitive bit width."""
    device = parse_device(
        PROJECT_ROOT / "examples" / "definitions" / "Device" / "PressureSensor.yml"
    )
    graph = resolve_modules(device)
    dictionary = allocate_object_dictionary(graph.namespace, graph.objects)
    pdos = resolve_pdo_mappings(
        resolve_pdo_references(graph), dictionary, resolve_module_graph_types(graph)
    )

    sensor_data = next(pdo for pdo in pdos if pdo.definition.key == "sensor_data")
    assert sensor_data.total_bits == 56
    assert sensor_data.entries[0].encoding == 0x22000020
    assert sensor_data.entries[1].encoding == 0x24E40008
    assert sensor_data.entries[2].encoding == 0x3AC10010


def test_pdo_rejects_payloads_larger_than_64_bits(tmp_path: Path) -> None:
    """Diagnostics identify the offending PDO and its resolved bit budget."""
    config = tmp_path / "TooLarge.yml"
    config.write_text(
        "\n".join(
            (
                "schema: 1",
                "device:",
                "  name: TooLarge",
                "objects:",
                "  first: {category: telemetry, type: uint32, access: ro}",
                "  second: {category: telemetry, type: uint32, access: ro}",
                "  third: {category: telemetry, type: uint32, access: ro}",
                "pdo:",
                "  tpdo:",
                "    oversized:",
                "      mapping: [first, second, third]",
                "",
            )
        ),
        encoding="utf-8",
    )
    device = parse_device(config)
    graph = resolve_modules(device)
    dictionary = allocate_object_dictionary(graph.namespace, graph.objects)

    with pytest.raises(PdoValidationError, match="TPDO 'oversized' exceeds maximum payload"):
        resolve_pdo_mappings(
            resolve_pdo_references(graph), dictionary, resolve_module_graph_types(graph)
        )
