"""Command-line interface for CanOpenGen development phases."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import cast

from canopengen.allocator import allocate_object_dictionary, diagnose_address
from canopengen.eds2od import run_eds2od
from canopengen.errors import AllocationError, CanOpenGenError, CppGenerationError
from canopengen.generators import generate_cpp_symbols, generate_eds, generate_markdown
from canopengen.generators.cpp import validate_cpp_identifier
from canopengen.model import (
    AllocatedObjectDictionary,
    DeviceDefinition,
    ModuleDefinition,
    ObjectCategory,
    ResolvedDefinitionTypes,
    ResolvedModuleGraph,
    ResolvedPdoDefinition,
)
from canopengen.odmap import format_address_diagnostic, format_object_dictionary_map
from canopengen.parser import parse_definition, parse_device
from canopengen.pdo import resolve_pdo_mappings
from canopengen.resolver import resolve_modules, resolve_pdo_references
from canopengen.type_resolver import resolve_module_graph_types


def _resolve_definition(
    definition: DeviceDefinition | ModuleDefinition,
) -> tuple[
    ResolvedModuleGraph,
    ResolvedDefinitionTypes,
    AllocatedObjectDictionary,
    tuple[ResolvedPdoDefinition, ...],
]:
    """Resolve modules, types, references, and addresses for one definition."""
    graph = resolve_modules(definition)
    resolved_types = resolve_module_graph_types(graph)
    try:
        dictionary = allocate_object_dictionary(graph.namespace, graph.objects)
    except AllocationError as error:
        raise AllocationError(f"{definition.source_path}: {error}") from error
    pdo_references = resolve_pdo_references(graph)
    resolve_pdo_mappings(pdo_references, dictionary, resolved_types)
    return graph, resolved_types, dictionary, pdo_references


def _validate(arguments: argparse.Namespace) -> int:
    """Run structural and available semantic validation for one definition file."""
    path = cast(Path, arguments.config)
    definition = parse_definition(path)
    _resolve_definition(definition)
    kind = "device" if isinstance(definition, DeviceDefinition) else "module"
    print(
        f"{path}: OK ({kind}, schema {definition.schema_version}; "
        "module/type/reference/address validation)"
    )
    return 0


def _project_yaml_files(project_root: Path) -> tuple[Path, ...]:
    """Discover project definitions in stable module-then-device order."""
    modules = sorted((project_root / "Modules").glob("*.yml"))
    devices = sorted((project_root / "Device").glob("*.yml"))
    return (*modules, *devices)


def _validate_all(arguments: argparse.Namespace) -> int:
    """Run all currently available validation for project YAML files."""
    project_root = cast(Path, arguments.project_root)
    paths = _project_yaml_files(project_root)
    print(
        "Validating CanOpenGen project (schema, module, type, reference, and address validation)..."
    )
    failures = 0
    for path in paths:
        try:
            definition = parse_definition(path)
            _resolve_definition(definition)
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


def _generate(arguments: argparse.Namespace) -> int:
    """Generate EDS and CANoopEn C++ output from one complete device definition."""
    config = cast(Path, arguments.config)
    artifact_name = config.stem
    try:
        validate_cpp_identifier(artifact_name, description="device filename stem")
    except CppGenerationError as error:
        raise CppGenerationError(
            f"invalid device filename '{config.name}': filename stem must be a valid "
            "C++ namespace identifier. Suggested name: PressureSensor.yml"
        ) from error
    device = parse_device(config)
    graph, resolved_types, dictionary, pdos = _resolve_definition(device)
    output_dir = cast(Path, arguments.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    eds_path = output_dir / f"{artifact_name}.eds"
    eds_path.write_text(
        generate_eds(device.name, dictionary, resolved_types),
        encoding="utf-8",
    )
    markdown_path = output_dir / f"{artifact_name}.md"
    markdown_path.write_text(
        generate_markdown(device, graph, dictionary, resolved_types, pdos),
        encoding="utf-8",
    )
    symbols_path = output_dir / f"{artifact_name}Objects.hpp"
    symbols_path.write_text(
        generate_cpp_symbols(artifact_name, dictionary, resolved_types),
        encoding="utf-8",
    )
    result = run_eds2od(
        eds_path,
        output_dir,
        artifact_name,
        executable=cast(Path | None, arguments.eds2od),
        cpp_namespace=cast(str | None, arguments.eds2od_namespace),
    )
    print(f"Generated {eds_path}")
    print(f"Generated {markdown_path}")
    print(f"Generated {symbols_path}")
    print(f"Generated {result.hpp_path}")
    print(f"Generated {result.cpp_path}")
    return 0


def _map(arguments: argparse.Namespace) -> int:
    """Allocate and print the complete device and imported-module dictionary."""
    device = parse_device(cast(Path, arguments.config))
    _, resolved_types, dictionary, _ = _resolve_definition(device)
    print(format_object_dictionary_map(dictionary, resolved_types), end="")
    return 0


def _address(arguments: argparse.Namespace) -> int:
    """Explain a CRC32 initial address and optional complete-context result."""
    qualified_name = cast(str, arguments.qualified_name)
    category = ObjectCategory(cast(str, arguments.category))
    raw_config = cast(Path | None, arguments.config)
    dictionary = None
    if raw_config is not None:
        device = parse_device(raw_config)
        _, _, dictionary, _ = _resolve_definition(device)
    diagnostic = diagnose_address(qualified_name, category, allocated=dictionary)
    print(format_address_diagnostic(diagnostic), end="")
    return 0


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

    generate_parser = subparsers.add_parser(
        "generate", help="generate EDS, Markdown, and CANoopEn C++ output"
    )
    generate_parser.add_argument("config", type=Path, help="Device YAML path")
    generate_parser.add_argument(
        "--output", type=Path, required=True, help="build output directory"
    )
    generate_parser.add_argument(
        "--eds2od-namespace",
        help="optional C++ namespace for an isolated remote CANoopEn Object Dictionary",
    )
    generate_parser.add_argument(
        "--eds2od",
        type=Path,
        help="optional Eds2Od executable (default: bundled tool or CANOPENGEN_EDS2OD)",
    )
    generate_parser.set_defaults(handler=_generate)

    map_parser = subparsers.add_parser("map", help="print the resolved Object Dictionary map")
    map_parser.add_argument("config", type=Path, help="Device YAML path")
    map_parser.set_defaults(handler=_map)

    address_parser = subparsers.add_parser("address", help="diagnose CRC32 address input")
    address_parser.add_argument("qualified_name", help="fully qualified object name")
    address_parser.add_argument(
        "--category",
        required=True,
        choices=("telemetry", "command", "configuration", "diagnostic"),
    )
    address_parser.add_argument("--config", type=Path, help="optional complete Device YAML context")
    address_parser.set_defaults(handler=_address)

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
