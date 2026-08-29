"""Invocation boundary for the bundled CANoopEn Eds2Od generator."""

from __future__ import annotations

import os
import shutil
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from canopengen.errors import Eds2OdExecutionError, Eds2OdUnavailableError


@dataclass(frozen=True, slots=True)
class Eds2OdResult:
    """Successful Eds2Od execution details retained for diagnostics and callers."""

    command: tuple[str, ...]
    cpp_path: Path
    hpp_path: Path
    stdout: str
    stderr: str


def _repository_root() -> Path:
    """Return the checkout root containing the bundled third-party tool."""
    return Path(__file__).parents[1]


def _bundled_command() -> tuple[str, ...]:
    """Find a native release binary or the bundled .NET project invocation."""
    root = _repository_root()
    executable_name = "Eds2Od.exe" if os.name == "nt" else "Eds2Od"
    binary = root / "third_party" / "Eds2Od" / "Build" / "Exe" / "linux-x64" / executable_name
    if binary.is_file():
        return (str(binary),)

    project = root / "third_party" / "Eds2Od" / "Eds2Od" / "Eds2Od.csproj"
    if project.is_file() and shutil.which("dotnet") is not None:
        return (
            "dotnet",
            "run",
            "--project",
            str(project),
            "--configuration",
            "Release",
            "--",
        )
    raise Eds2OdUnavailableError(
        "Eds2Od is unavailable; set CANOPENGEN_EDS2OD to an executable, add a bundled "
        "release binary, or install the .NET SDK required by third_party/Eds2Od"
    )


def _command_prefix(executable: str | Path | Sequence[str] | None) -> tuple[str, ...]:
    """Resolve one explicit/environment/bundled Eds2Od command without a shell."""
    if executable is not None:
        if isinstance(executable, (str, Path)):
            return (str(executable),)
        if not executable:
            raise Eds2OdUnavailableError("Eds2Od command cannot be empty")
        return tuple(executable)
    configured = os.environ.get("CANOPENGEN_EDS2OD")
    if configured:
        return (configured,)
    return _bundled_command()


def _failure_detail(stdout: str, stderr: str) -> str:
    """Compress captured process output into a useful user-facing diagnostic suffix."""
    messages = tuple(part.strip() for part in (stderr, stdout) if part.strip())
    return "\n".join(messages)


def run_eds2od(
    eds_path: str | Path,
    output_dir: str | Path,
    device_name: str,
    *,
    executable: str | Path | Sequence[str] | None = None,
) -> Eds2OdResult:
    """Generate CANoopEn C++ Object Dictionary files from a compatible EDS.

    The bundled tool accepts exactly ``<eds-file> <output-cpp> <output-hpp>``. This
    wrapper captures both output streams, reports non-zero exits as CanOpenGen errors,
    and verifies the generated artifacts before returning.

    @param eds_path Input EDS generated from resolved CanOpenGen IR.
    @param output_dir Directory that will receive ``<device>NameOd.cpp/.hpp``.
    @param device_name Device namespace used for deterministic C++ file names.
    @param executable Optional executable or complete command prefix for tests/tooling.
    @return Captured successful invocation result and generated C++ paths.
    @raises Eds2OdError If the tool is unavailable, fails, or misses an output file.
    """
    source = Path(eds_path)
    if not source.is_file():
        raise Eds2OdExecutionError(f"EDS input does not exist: {source}")
    if not device_name or Path(device_name).name != device_name:
        raise Eds2OdExecutionError(
            f"invalid device name '{device_name}'; generated C++ output names must be one path stem"
        )

    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    cpp_path = destination / f"{device_name}Od.cpp"
    hpp_path = destination / f"{device_name}Od.hpp"
    command = (*_command_prefix(executable), str(source), str(cpp_path), str(hpp_path))
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except OSError as error:
        raise Eds2OdUnavailableError(
            f"cannot execute Eds2Od command '{command[0]}': {error}"
        ) from error

    if completed.returncode != 0:
        detail = _failure_detail(completed.stdout, completed.stderr)
        raise Eds2OdExecutionError(
            f"Eds2Od failed with exit status {completed.returncode} while reading {source}"
            + (f":\n{detail}" if detail else "")
        )
    missing = tuple(path for path in (cpp_path, hpp_path) if not path.is_file())
    if missing:
        raise Eds2OdExecutionError(
            "Eds2Od completed without generating expected output: "
            + ", ".join(str(path) for path in missing)
        )
    return Eds2OdResult(
        command=command,
        cpp_path=cpp_path,
        hpp_path=hpp_path,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )
