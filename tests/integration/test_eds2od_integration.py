"""Real bundled Eds2Od acceptance test for the reference device EDS."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from canopengen.allocator import allocate_object_dictionary
from canopengen.eds2od import run_eds2od
from canopengen.generators import generate_eds
from canopengen.parser import parse_device
from canopengen.resolver import resolve_modules
from canopengen.type_resolver import resolve_module_graph_types

PROJECT_ROOT = Path(__file__).parents[2]
EXAMPLE_DEFINITIONS = PROJECT_ROOT / "examples" / "definitions"
EDS2OD_PROJECT = PROJECT_ROOT / "third_party" / "Eds2Od" / "Eds2Od" / "Eds2Od.csproj"


def _dotnet_10_available() -> bool:
    """Check whether this host can build the bundled net10.0 Eds2Od project."""
    if shutil.which("dotnet") is None:
        return False
    result = subprocess.run(
        ("dotnet", "--list-sdks"),
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return any(line.startswith("10.") for line in result.stdout.splitlines())


@pytest.mark.skipif(
    not EDS2OD_PROJECT.is_file() or not _dotnet_10_available(),
    reason="real Eds2Od integration requires the bundled source and .NET SDK 10",
)
def test_pressure_sensor_eds_is_accepted_by_real_eds2od(tmp_path: Path) -> None:
    """Generate the complete example EDS and require the actual CANoopEn tool to accept it."""
    device = parse_device(EXAMPLE_DEFINITIONS / "Device" / "PressureSensor.yml")
    graph = resolve_modules(device)
    resolved_types = resolve_module_graph_types(graph)
    dictionary = allocate_object_dictionary(graph.namespace, graph.objects)
    eds_path = tmp_path / "PressureSensor.eds"
    eds_path.write_text(
        generate_eds(device.name, dictionary, resolved_types),
        encoding="utf-8",
    )

    result = run_eds2od(eds_path, tmp_path / "generated", device.name)

    assert result.cpp_path.is_file()
    assert result.hpp_path.is_file()
    assert "CoOdEntryUnsigned32" in result.hpp_path.read_text(encoding="utf-8")
    assert "AddEntry" in result.cpp_path.read_text(encoding="utf-8")
