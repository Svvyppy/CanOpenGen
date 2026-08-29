"""Tests for the Phase 1 command-line skeleton."""

from pathlib import Path

import pytest

from canopengen.cli import main

PROJECT_ROOT = Path(__file__).parents[2]


def test_validate_command(capsys: pytest.CaptureFixture[str]) -> None:
    """Single-file validation identifies the parsed kind and schema version."""
    result = main(["validate", str(PROJECT_ROOT / "Device" / "PressureSensor.yml")])

    output = capsys.readouterr()
    assert result == 0
    assert "OK (device, schema 1; structural validation)" in output.out
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


@pytest.mark.parametrize(
    "command", [["map", "Device.yml"], ["address", "Device.value", "--category", "telemetry"]]
)
def test_deferred_commands_are_visible_but_fail_clearly(
    command: list[str],
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The stable CLI shape does not pretend deferred functionality exists."""
    result = main(command)

    output = capsys.readouterr()
    assert result == 1
    assert "not available until Phase 2 address allocation" in output.err
