"""Immutable reusable-module dependency resolution results."""

from __future__ import annotations

from dataclasses import dataclass

from canopengen.model.device import DeviceDefinition
from canopengen.model.module import ModuleDefinition, ModuleParameter, ParameterValue
from canopengen.model.object import ObjectDefinition
from canopengen.model.pdo import PdoDefinition


@dataclass(frozen=True, slots=True)
class ResolvedModule:
    """One uniquely configured module in a resolved dependency graph."""

    definition: ModuleDefinition
    parameters: tuple[ModuleParameter, ...]
    dependencies: tuple[str, ...]

    @property
    def namespace(self) -> str:
        """Return the filename-derived module identity."""
        return self.definition.namespace

    def parameter(self, name: str) -> ParameterValue:
        """Return one supplied scalar parameter or raise ``KeyError`` if absent."""
        for parameter in self.parameters:
            if parameter.name == name:
                return parameter.value
        raise KeyError(name)


@dataclass(frozen=True, slots=True)
class ResolvedModuleGraph:
    """A root definition plus its deterministic, dependency-first module closure."""

    root: DeviceDefinition | ModuleDefinition
    root_dependencies: tuple[str, ...]
    modules: tuple[ResolvedModule, ...]

    @property
    def namespace(self) -> str:
        """Return the namespace used for diagnostics and the combined dictionary."""
        if isinstance(self.root, DeviceDefinition):
            return self.root.name
        return self.root.namespace

    @property
    def definitions(self) -> tuple[DeviceDefinition | ModuleDefinition, ...]:
        """Return the root followed by imported module definitions."""
        return (self.root, *(module.definition for module in self.modules))

    @property
    def objects(self) -> tuple[ObjectDefinition, ...]:
        """Return all root and imported objects as one allocation input."""
        return tuple(
            object_definition
            for definition in self.definitions
            for object_definition in definition.objects
        )

    @property
    def pdos(self) -> tuple[PdoDefinition, ...]:
        """Return all root and imported PDO declarations."""
        return tuple(pdo for definition in self.definitions for pdo in definition.pdos)

    def module(self, namespace: str) -> ResolvedModule | None:
        """Return an imported module by filename namespace."""
        return next((module for module in self.modules if module.namespace == namespace), None)

    def definition(self, namespace: str) -> DeviceDefinition | ModuleDefinition | None:
        """Return a root or imported definition by identity namespace."""
        if namespace == self.namespace:
            return self.root
        module = self.module(namespace)
        return module.definition if module is not None else None

    def visible_namespaces(self, owner_namespace: str) -> tuple[str, ...]:
        """Return the owner's local namespace and transitive dependency visibility."""
        if owner_namespace == self.namespace:
            pending = list(self.root_dependencies)
        else:
            owner = self.module(owner_namespace)
            if owner is None:
                raise KeyError(owner_namespace)
            pending = list(owner.dependencies)

        visible = {owner_namespace}
        while pending:
            namespace = pending.pop()
            if namespace in visible:
                continue
            visible.add(namespace)
            dependency = self.module(namespace)
            if dependency is not None:
                pending.extend(dependency.dependencies)
        return (owner_namespace, *sorted(visible - {owner_namespace}))
