"""Tests for structural validation and Phase 2 allocation commands."""

from pathlib import Path

import pytest

from canopengen.cli import main
from canopengen.eds2od import Eds2OdResult

PROJECT_ROOT = Path(__file__).parents[2]


def test_validate_command(capsys: pytest.CaptureFixture[str]) -> None:
    """Single-file validation identifies the parsed kind and schema version."""
    result = main(["validate", str(PROJECT_ROOT / "Device" / "PressureSensor.yml")])

    output = capsys.readouterr()
    assert result == 0
    assert "module/type/reference/address validation" in output.out
    assert not output.err


def test_validate_all_command(capsys: pytest.CaptureFixture[str]) -> None:
    """Project discovery validates modules before devices in stable order."""
    result = main(["validate-all", "--project-root", str(PROJECT_ROOT)])

    output = capsys.readouterr()
    assert result == 0
    assert "4 files validated successfully" in output.out
    assert output.out.index("Modules/CommonTypes.yml") < output.out.index(
        "Device/PressureSensor.yml"
    )


def test_validate_command_returns_nonzero_for_invalid_file(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Expected diagnostics become concise stderr and a non-zero status."""
    path = tmp_path / "Invalid.yml"
    path.write_text("schema: 2\ndevice:\n  name: Invalid\n", encoding="utf-8")

    result = main(["validate", str(path)])

    output = capsys.readouterr()
    assert result == 1
    assert "unsupported schema version 2" in output.err


def test_validate_command_runs_address_validation(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Phase 2 validation rejects manual indexes outside their category range."""
    path = tmp_path / "InvalidAddress.yml"
    path.write_text(
        """schema: 1
device:
  name: InvalidAddress
objects:
  value:
    category: telemetry
    type: uint8
    access: ro
    index: 0x3000
""",
        encoding="utf-8",
    )

    result = main(["validate", str(path)])

    output = capsys.readouterr()
    assert result == 1
    assert str(path) in output.err
    assert "outside telemetry range" in output.err


def test_validate_command_runs_type_resolution(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Phase 3 validation rejects unknown object datatypes contextually."""
    path = tmp_path / "UnknownType.yml"
    path.write_text(
        """schema: 1
device:
  name: UnknownType
objects:
  value:
    category: telemetry
    type: Missing
    access: ro
""",
        encoding="utf-8",
    )

    result = main(["validate", str(path)])

    output = capsys.readouterr()
    assert result == 1
    assert str(path) in output.err
    assert "object 'UnknownType.value' references unknown datatype 'Missing'" in output.err


def test_generate_command_writes_eds_and_cplusplus_output(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Generation uses resolved IR and delegates C++ output to the Eds2Od boundary."""

    def fake_eds2od(
        eds_path: Path, output_dir: Path, device_name: str, **_: object
    ) -> Eds2OdResult:
        cpp_path = output_dir / f"{device_name}Od.cpp"
        hpp_path = output_dir / f"{device_name}Od.hpp"
        cpp_path.write_text("// generated source\n", encoding="utf-8")
        hpp_path.write_text("// generated header\n", encoding="utf-8")
        return Eds2OdResult(
            command=("fake-eds2od", str(eds_path)),
            cpp_path=cpp_path,
            hpp_path=hpp_path,
            stdout="",
            stderr="",
        )

    monkeypatch.setattr("canopengen.cli.run_eds2od", fake_eds2od)
    output_dir = tmp_path / "canopen"
    result = main(
        [
            "generate",
            str(PROJECT_ROOT / "Device" / "PressureSensor.yml"),
            "--output",
            str(output_dir),
        ]
    )

    output = capsys.readouterr()
    assert result == 0
    assert (output_dir / "PressureSensor.eds").is_file()
    assert (output_dir / "PressureSensorOd.cpp").is_file()
    assert (output_dir / "PressureSensorOd.hpp").is_file()
    assert "Generated" in output.out
    assert "[2200]" in (output_dir / "PressureSensor.eds").read_text(encoding="utf-8")


def test_map_command(capsys: pytest.CaptureFixture[str]) -> None:
    """The map command displays device and imported-module objects."""
    result = main(["map", str(PROJECT_ROOT / "Device" / "PressureSensor.yml")])

    output = capsys.readouterr()
    assert result == 0
    assert "PressureSensor Object Dictionary" in output.out
    assert "0x2200:00  pressure                 uint32 (Pressure)" in output.out
    assert "0x3129:01    offset" in output.out
    assert "[auto, crc32]" in output.out
    assert "supply_voltage" in output.out
    assert "firmware_version" in output.out
    assert "uint32 (FirmwareVersion)" in output.out


def test_address_command_without_context(capsys: pytest.CaptureFixture[str]) -> None:
    """Address diagnostics lock the public canonical CRC32 inputs."""
    result = main(["address", "PressureSensor.pressure", "--category", "telemetry"])

    output = capsys.readouterr()
    assert result == 0
    assert "Canonical hash key: telemetry:PressureSensor.pressure" in output.out
    assert "CRC32: 0xA66C98DF" in output.out
    assert "Initial CANopen index: 0x20DF" in output.out
    assert "Final CANopen index" not in output.out


def test_address_command_with_context(capsys: pytest.CaptureFixture[str]) -> None:
    """Complete context shows explicit overrides and post-probing addresses."""
    result = main(
        [
            "address",
            "PressureSensor.pressure",
            "--category",
            "telemetry",
            "--config",
            str(PROJECT_ROOT / "Device" / "PressureSensor.yml"),
        ]
    )

    output = capsys.readouterr()
    assert result == 0
    assert "Final CANopen index: 0x2200" in output.out
    assert "Allocation source: explicit" in output.out
    assert "Probe distance: 0" in output.out
