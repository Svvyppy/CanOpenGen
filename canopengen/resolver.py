"""Recursive module loading and symbolic reference resolution."""

from __future__ import annotations

from pathlib import Path

from canopengen.errors import (
    AmbiguousReferenceError,
    DuplicateModuleImportError,
    InvalidModuleNameError,
    ModuleDependencyCycleError,
    ModuleParameterConflictError,
    NamespaceCollisionError,
    UnknownModuleError,
    UnknownReferenceError,
)
from canopengen.model import (
    DeviceDefinition,
    ModuleDefinition,
    ModuleImport,
    ModuleParameter,
    ResolvedModule,
    ResolvedModuleGraph,
    ResolvedObjectReference,
    ResolvedPdoDefinition,
)
from canopengen.parser import parse_module


def _definition_namespace(definition: DeviceDefinition | ModuleDefinition) -> str:
    """Return the identity namespace assigned by the parser."""
    if isinstance(definition, DeviceDefinition):
        return definition.name
    return definition.namespace


def _default_modules_directory(source_path: Path) -> Path:
    """Infer the conventional project ``Modules`` directory from a source path."""
    if source_path.parent.name == "Modules":
        return source_path.parent
    if source_path.parent.name == "Device":
        return source_path.parent.parent / "Modules"
    return source_path.parent / "Modules"


def _validate_direct_imports(
    owner: DeviceDefinition | ModuleDefinition,
) -> tuple[ModuleImport, ...]:
    """Reject duplicate declarations while returning lexical traversal order."""
    seen: set[str] = set()
    for module_import in owner.imports:
        if module_import.name in seen:
            raise DuplicateModuleImportError(
                f"{owner.source_path}: '{_definition_namespace(owner)}' imports module "
                f"'{module_import.name}' more than once; keep one import declaration"
            )
        seen.add(module_import.name)
    return tuple(sorted(owner.imports, key=lambda item: item.name))


def _module_path(modules_directory: Path, name: str, *, source_path: Path) -> Path:
    """Map one safe namespace to its conventional YAML source path."""
    if not name or name in {".", ".."} or "/" in name or "\\" in name or name.endswith(".yml"):
        raise InvalidModuleNameError(
            f"{source_path}: invalid module name '{name}'; use a filename stem without "
            "directories or the .yml suffix"
        )
    return modules_directory / f"{name}.yml"


def _format_parameters(parameters: tuple[ModuleParameter, ...]) -> str:
    """Format an immutable module configuration for conflict diagnostics."""
    if not parameters:
        return "{}"
    assignments = ", ".join(f"{parameter.name}={parameter.value!r}" for parameter in parameters)
    return "{" + assignments + "}"


class _ModuleResolver:
    """Per-run DFS state for recursive module resolution."""

    def __init__(
        self,
        root: DeviceDefinition | ModuleDefinition,
        modules_directory: Path,
    ) -> None:
        self._root = root
        self._modules_directory = modules_directory
        self._parsed: dict[str, ModuleDefinition] = {}
        self._configurations: dict[str, tuple[ModuleParameter, ...]] = {}
        self._configuration_sources: dict[str, str] = {}
        self._resolved: dict[str, ResolvedModule] = {}
        self._ordered: list[ResolvedModule] = []
        self._stack: list[str] = []

    def resolve(self) -> ResolvedModuleGraph:
        """Resolve the root's complete dependency closure."""
        root_namespace = _definition_namespace(self._root)
        if isinstance(self._root, ModuleDefinition):
            self._parsed[root_namespace] = self._root
            self._configurations[root_namespace] = ()
            self._configuration_sources[root_namespace] = str(self._root.source_path)
            self._stack.append(root_namespace)

        root_imports = _validate_direct_imports(self._root)
        for module_import in root_imports:
            self._resolve_import(module_import, owner=self._root)

        if isinstance(self._root, ModuleDefinition):
            popped = self._stack.pop()
            if popped != root_namespace:
                raise AssertionError("module resolver recursion stack is inconsistent")

        if isinstance(self._root, DeviceDefinition) and root_namespace in self._resolved:
            module = self._resolved[root_namespace]
            raise NamespaceCollisionError(
                f"{self._root.source_path}: device namespace '{root_namespace}' collides with "
                f"module filename '{module.definition.source_path.name}'; rename either one"
            )

        return ResolvedModuleGraph(
            root=self._root,
            root_dependencies=tuple(module_import.name for module_import in root_imports),
            modules=tuple(self._ordered),
        )

    def _resolve_import(
        self,
        module_import: ModuleImport,
        *,
        owner: DeviceDefinition | ModuleDefinition,
    ) -> None:
        """Load and recursively resolve one import, deduplicating equal diamonds."""
        namespace = module_import.name
        if namespace in self._stack:
            cycle_start = self._stack.index(namespace)
            cycle = (*self._stack[cycle_start:], namespace)
            raise ModuleDependencyCycleError(
                f"{owner.source_path}: module dependency cycle: {' -> '.join(cycle)}"
            )

        previous_configuration = self._configurations.get(namespace)
        if previous_configuration is not None:
            if previous_configuration != module_import.parameters:
                raise ModuleParameterConflictError(
                    f"{owner.source_path}: module '{namespace}' is imported with conflicting "
                    f"parameters {_format_parameters(module_import.parameters)}; first resolved "
                    f"as {_format_parameters(previous_configuration)} from "
                    f"{self._configuration_sources[namespace]}"
                )
            if namespace in self._resolved:
                return

        module_path = _module_path(
            self._modules_directory,
            namespace,
            source_path=owner.source_path,
        )
        if not module_path.is_file():
            raise UnknownModuleError(
                f"{owner.source_path}: '{_definition_namespace(owner)}' imports unknown module "
                f"'{namespace}'; expected {module_path}"
            )

        definition = self._parsed.get(namespace)
        if definition is None:
            definition = parse_module(module_path)
            self._parsed[namespace] = definition
        self._configurations[namespace] = module_import.parameters
        self._configuration_sources[namespace] = (
            f"{owner.source_path} ({_definition_namespace(owner)})"
        )

        self._stack.append(namespace)
        imports = _validate_direct_imports(definition)
        for dependency in imports:
            self._resolve_import(dependency, owner=definition)
        popped = self._stack.pop()
        if popped != namespace:
            raise AssertionError("module resolver recursion stack is inconsistent")

        resolved = ResolvedModule(
            definition=definition,
            parameters=module_import.parameters,
            dependencies=tuple(dependency.name for dependency in imports),
        )
        self._resolved[namespace] = resolved
        self._ordered.append(resolved)


def resolve_modules(
    root: DeviceDefinition | ModuleDefinition,
    *,
    modules_directory: str | Path | None = None,
) -> ResolvedModuleGraph:
    """Load a definition's recursive module closure.

    Equal transitive imports are emitted once. Direct duplicate declarations, cycles,
    missing files, and conflicting parameter configurations fail explicitly.

    @param root Parsed Device or Module definition to resolve.
    @param modules_directory Optional override for the conventional ``Modules`` path.
    @return Immutable dependency-first module graph.
    @raises ModuleResolutionError If imports cannot form one unambiguous graph.
    """
    directory = (
        Path(modules_directory)
        if modules_directory is not None
        else _default_modules_directory(root.source_path)
    )
    return _ModuleResolver(root, directory).resolve()


def resolve_pdo_references(
    graph: ResolvedModuleGraph,
) -> tuple[ResolvedPdoDefinition, ...]:
    """Resolve local, qualified, and uniquely imported PDO object references.

    Local object keys win within the PDO owner's namespace. Imported unqualified names
    must have exactly one visible match; explicit qualified names must identify a visible
    object or record field.

    @param graph Fully loaded module graph.
    @return PDO declarations paired with qualified mapping targets.
    @raises ReferenceResolutionError For unknown or ambiguous mappings.
    """
    targets_by_namespace = {
        (
            definition.name if isinstance(definition, DeviceDefinition) else definition.namespace
        ): tuple(
            target
            for object_definition in definition.objects
            for target in (
                object_definition.qualified_name,
                *(field.qualified_name for field in object_definition.fields),
            )
        )
        for definition in graph.definitions
    }
    resolved_pdos: list[ResolvedPdoDefinition] = []
    for pdo in graph.pdos:
        owner_definition = graph.definition(pdo.owner_namespace)
        if owner_definition is None:
            raise AssertionError(f"unknown PDO owner namespace '{pdo.owner_namespace}'")
        visible = frozenset(graph.visible_namespaces(pdo.owner_namespace))
        visible_targets = tuple(
            (namespace, target)
            for namespace in sorted(visible)
            for target in targets_by_namespace[namespace]
        )
        qualified_targets = frozenset(target for _, target in visible_targets)
        mapping: list[ResolvedObjectReference] = []
        for reference in pdo.mapping:
            local_name = f"{pdo.owner_namespace}.{reference}"
            if local_name in qualified_targets:
                match = local_name
            elif reference in qualified_targets:
                match = reference
            else:
                candidates = tuple(
                    sorted(
                        target
                        for namespace, target in visible_targets
                        if target.removeprefix(f"{namespace}.") == reference
                    )
                )
                if not candidates:
                    raise UnknownReferenceError(
                        f"{owner_definition.source_path}: {pdo.direction.value.upper()} "
                        f"'{pdo.key}' references unknown object '{reference}' from namespace "
                        f"'{pdo.owner_namespace}'"
                    )
                if len(candidates) > 1:
                    raise AmbiguousReferenceError(
                        f"{owner_definition.source_path}: {pdo.direction.value.upper()} "
                        f"'{pdo.key}' reference '{reference}' is ambiguous: "
                        f"{', '.join(candidates)}; use a qualified reference"
                    )
                match = candidates[0]
            mapping.append(ResolvedObjectReference(declared_name=reference, qualified_name=match))
        resolved_pdos.append(ResolvedPdoDefinition(definition=pdo, mapping=tuple(mapping)))
    return tuple(resolved_pdos)
