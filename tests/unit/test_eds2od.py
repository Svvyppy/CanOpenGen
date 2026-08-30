"""Tests for Eds2Od process invocation and diagnostics."""

from pathlib import Path

import pytest

from canopengen.eds2od import run_eds2od
from canopengen.errors import Eds2OdExecutionError


def _tool_script(tmp_path: Path, body: str) -> Path:
    """Create one narrow fake Eds2Od executable for process-boundary tests."""
    script = tmp_path / "fake-eds2od"
    script.write_text(f"#!/usr/bin/env sh\nset -eu\n{body}\n", encoding="utf-8")
    script.chmod(0o755)
    return script


def test_runner_captures_success_and_verifies_generated_outputs(tmp_path: Path) -> None:
    """The wrapper passes the documented argument order and returns both streams."""
    eds_path = tmp_path / "Device.eds"
    eds_path.write_text("[2000]\nDataType=0x0005\n", encoding="utf-8")
    tool = _tool_script(
        tmp_path,
        (
            "printf '// cpp\\n' > \"$2\"\nprintf '// hpp\\n' > \"$3\"\n"
            "printf 'ok\\n'\nprintf 'warning\\n' >&2"
        ),
    )

    result = run_eds2od(eds_path, tmp_path / "output", "Device", executable=tool)

    assert result.command[0] == str(tool)
    assert result.cpp_path.read_text(encoding="utf-8") == "// cpp\n"
    assert result.hpp_path.read_text(encoding="utf-8") == "// hpp\n"
    assert result.stdout == "ok\n"
    assert result.stderr == "warning\n"


def test_runner_surfaces_nonzero_exit_and_captured_stderr(tmp_path: Path) -> None:
    """Tool failures preserve the exit status and actionable diagnostic output."""
    eds_path = tmp_path / "Device.eds"
    eds_path.write_text("[2000]\nDataType=0x0005\n", encoding="utf-8")
    tool = _tool_script(tmp_path, "printf 'bad EDS\\n' >&2\nexit 7")

    with pytest.raises(Eds2OdExecutionError, match=r"exit status 7[\s\S]*bad EDS"):
        run_eds2od(eds_path, tmp_path / "output", "Device", executable=tool)


def test_runner_wraps_a_remote_dictionary_in_the_requested_namespace(tmp_path: Path) -> None:
    """Remote dictionaries have their own namespace while stack types stay qualified."""
    eds_path = tmp_path / "Device.eds"
    eds_path.write_text("[2000]\nDataType=0x0005\n", encoding="utf-8")
    tool = _tool_script(
        tmp_path,
        (
            "printf 'namespace CANoopEn\\n{\\n\\nclass DeviceOd : public "
            'CoObjectDictionary\\n\' > "$3"\n'
            "printf 'using namespace CANoopEn;\\nDeviceOd::DeviceOd() :\\n    "
            'CoObjectDictionary(listener),\\n{}\\n\' > "$2"'
        ),
    )

    result = run_eds2od(
        eds_path,
        tmp_path / "output",
        "Device",
        executable=tool,
        cpp_namespace="PressureSensor",
    )

    assert "namespace PressureSensor" in result.hpp_path.read_text(encoding="utf-8")
    assert "public CANoopEn::CoObjectDictionary" in result.hpp_path.read_text(encoding="utf-8")
    source = result.cpp_path.read_text(encoding="utf-8")
    assert "using namespace PressureSensor;" in source
    assert "CANoopEn::CoObjectDictionary(listener)" in source

    result = run_eds2od(
        eds_path,
        tmp_path / "output",
        "Device",
        executable=tool,
        cpp_namespace="PressureSensor",
    )
    assert "namespace PressureSensor" in result.hpp_path.read_text(encoding="utf-8")
