"""Black-box tests for the public external-definitions CMake API."""

from __future__ import annotations

import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[2]


def _write(path: Path, text: str) -> None:
    """Write a small, explicit integration-test fixture."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_canopen_firmware_generates_isolated_local_and_remote_outputs(tmp_path: Path) -> None:
    """A firmware consumes external YAML and namespaces every remote OD by file stem."""
    definitions = tmp_path / "CanOpenDefinitions"
    for name in ("MainController", "MotorController"):
        _write(
            definitions / "Device" / f"{name}.yml",
            f"""schema: 1
device:
  name: Display {name}
objects:
  value:
    category: telemetry
    type: uint16
    access: rw
""",
        )
    _write(
        definitions / "Modules" / "Empty.yml",
        "schema: 1\nmodule:\n  name: Empty\n",
    )
    eds2od = tmp_path / "fake-eds2od"
    _write(
        eds2od,
        """#!/usr/bin/env sh
set -eu
printf 'namespace CANoopEn\\n{\\n\\nclass GeneratedOd : public CoObjectDictionary\\n' > "$3"
printf 'using namespace CANoopEn;\\nGeneratedOd::GeneratedOd() :\\n' > "$2"
printf '    CoObjectDictionary(listener),\\n{}\\n' >> "$2"
""",
    )
    eds2od.chmod(0o755)
    firmware = tmp_path / "Firmware"
    _write(
        firmware / "CMakeLists.txt",
        f"""cmake_minimum_required(VERSION 3.20)
project(Firmware LANGUAGES NONE)
include(\"{PROJECT_ROOT}/cmake/CanOpenGen.cmake\")
canopen_firmware(
  TARGET main_controller
  LOCAL MainController
  REMOTE MotorController
  DEFINITIONS_DIR \"{definitions}\"
)
""",
    )
    build = tmp_path / "build"
    configured = subprocess.run(
        (
            "cmake",
            "-S",
            str(firmware),
            "-B",
            str(build),
            f"-DCANOPENGEN_EDS2OD={eds2od}",
        ),
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert configured.returncode == 0, configured.stderr
    built = subprocess.run(
        ("cmake", "--build", str(build), "--target", "main_controller_canopen"),
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert built.returncode == 0, built.stderr

    local = build / "generated" / "canopen" / "MainController"
    remote = build / "generated" / "canopen" / "MotorController"
    assert (local / "MainControllerObjects.hpp").is_file()
    assert (local / "MainControllerOd.hpp").is_file()
    assert (remote / "MotorControllerObjects.hpp").is_file()
    remote_header = (remote / "MotorControllerOd.hpp").read_text(encoding="utf-8")
    assert "namespace MotorController" in remote_header
    assert "CANoopEn::CoObjectDictionary" in remote_header
