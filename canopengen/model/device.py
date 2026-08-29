"""Raw top-level CANopen device model."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from canopengen.model.datatype import CustomTypeDefinition
from canopengen.model.module import ModuleImport
from canopengen.model.object import ObjectDefinition
from canopengen.model.pdo import PdoDefinition


@dataclass(frozen=True, slots=True)
class DeviceDefinition:
    """A structurally validated device before module/type/address resolution."""

    schema_version: int
    name: str
    source_path: Path
    info: str | None = None
    imports: tuple[ModuleImport, ...] = ()
    types: tuple[CustomTypeDefinition, ...] = ()
    objects: tuple[ObjectDefinition, ...] = ()
    pdos: tuple[PdoDefinition, ...] = ()
