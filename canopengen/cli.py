"""Command-line interface for CanOpenGen development phases."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import cast

from canopengen.errors import CanOpenGenError, CommandUnavailableError
from canopengen.model import DeviceDefinition
from canopengen.parser import parse_definition


def _validate(arguments: argparse.Namespace) -> int:
    """Run Phase 1 structural validation for one definition file."""
    path = cast(Path, arguments.config)
    definition = parse_definition(path)
    kind = "device" if isinstance(definition, DeviceDefinition) else "module"
    print(f"{path}: OK ({kind}, schema {definition.schema_version}; structural validation)")
    return 0


def _project_yaml_files(project_root: Path) -> tuple[Path, ...]:
    """Discover project definitions in stable module-then-device order."""
    modules = sorted((project_root / "Modules").glob("*.yml"))
    devices = sorted((project_root / "Device").glob("*.yml"))
    return (*modules, *devices)


def _validate_all(arguments: argparse.Namespace) -> int:
    """Run Phase 1 structural validation for all project YAML files."""
    project_root = cast(Path, arguments.project_root)
    paths = _project_yaml_files(project_root)
    print("Validating CanOpenGen project (structural Phase 1 validation)...")
    failures = 0
    for path in paths:
        try:
            parse_definition(path)
        except CanOpenGenError as error:
            failures += 1
            print(f"{path}    FAILED", file=sys.stderr)
            print(f"  {error}", file=sys.stderr)
        else:
            print(f"{path}    OK")

    if failures:
        print(f"{failures} of {len(paths)} files failed validation.", file=sys.stderr)
        return 1
    print(f"{len(paths)} files validated successfully.")
    return 0


def _unavailable(arguments: argparse.Namespace) -> int:
    """Report commands intentionally deferred beyond Phase 1."""
    command = cast(str, arguments.command)
    phases = {
        "map": "Phase 2 address allocation",
        "address": "Phase 2 address allocation",
        "generate": "Phase 5 EDS/Eds2Od generation",
    }
    raise CommandUnavailableError(f"'{command}' is not available until {phases[command]}")


def build_argument_parser() -> argparse.ArgumentParser:
    """Build the stable top-level CLI shape used across implementation phases."""
    parser = argparse.ArgumentParser(
        prog="canopengen",
        description="Generate CANopen Object Dictionaries from versioned YAML.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate", help="validate one definition")
    validate_parser.add_argument("config", type=Path, help="Device or Module YAML path")
    validate_parser.set_defaults(handler=_validate)

    validate_all_parser = subparsers.add_parser(
        "validate-all", help="validate all Device/*.yml and Modules/*.yml definitions"
    )
    validate_all_parser.add_argument(
        "--project-root",
        type=Path,
        default=Path.cwd(),
        help="project root containing Device/ and Modules/ (default: current directory)",
    )
    validate_all_parser.set_defaults(handler=_validate_all)

    generate_parser = subparsers.add_parser("generate", help="generate build artifacts")
    generate_parser.add_argument("config", type=Path, help="Device YAML path")
    generate_parser.add_argument(
        "--output", type=Path, required=True, help="build output directory"
    )
    generate_parser.set_defaults(handler=_unavailable)

    map_parser = subparsers.add_parser("map", help="print the resolved Object Dictionary map")
    map_parser.add_argument("config", type=Path, help="Device YAML path")
    map_parser.set_defaults(handler=_unavailable)

    address_parser = subparsers.add_parser("address", help="diagnose CRC32 address input")
    address_parser.add_argument("qualified_name", help="fully qualified object name")
    address_parser.add_argument(
        "--category",
        required=True,
        choices=("telemetry", "command", "configuration", "diagnostic"),
    )
    address_parser.add_argument("--config", type=Path, help="optional complete Device YAML context")
    address_parser.set_defaults(handler=_unavailable)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run CanOpenGen and convert expected diagnostics to a non-zero exit status."""
    parser = build_argument_parser()
    arguments = parser.parse_args(argv)
    handler = cast(Callable[[argparse.Namespace], int], arguments.handler)
    try:
        return handler(arguments)
    except CanOpenGenError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
