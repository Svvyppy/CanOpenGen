"""Raw reusable module models."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TypeAlias

from canopengen.model.datatype import CustomTypeDefinition
from canopengen.model.object import ObjectDefinition
from canopengen.model.pdo import PdoDefinition

ParameterValue: TypeAlias = str | int | float | bool | None


@dataclass(frozen=True, slots=True)
class ModuleParameter:
    """One future-facing scalar module parameter assignment."""

    name: str
    value: ParameterValue


@dataclass(frozen=True, slots=True)
class ModuleImport:
    """An unresolved module dependency and its scalar arguments."""

    name: str
    parameters: tuple[ModuleParameter, ...] = ()


@dataclass(frozen=True, slots=True)
class ModuleDefinition:
    """A structurally validated reusable module before dependency resolution.

    ``namespace`` comes from the filename stem and is the module's identity.
    ``name`` is display metadata from YAML and is never used as the namespace.
    """

    schema_version: int
    namespace: str
    name: str
    source_path: Path
    info: str | None = None
    imports: tuple[ModuleImport, ...] = ()
    types: tuple[CustomTypeDefinition, ...] = ()
    objects: tuple[ObjectDefinition, ...] = ()
    pdos: tuple[PdoDefinition, ...] = ()
