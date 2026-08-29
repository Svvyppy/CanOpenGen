"""Unresolved Object Dictionary object declarations."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Access(StrEnum):
    """Schema-v1 CANopen object access modes."""

    READ_ONLY = "ro"
    WRITE_ONLY = "wo"
    READ_WRITE = "rw"


class ObjectCategory(StrEnum):
    """Application object categories with stable schema-v1 index partitions."""

    TELEMETRY = "telemetry"
    COMMAND = "command"
    CONFIGURATION = "configuration"
    DIAGNOSTIC = "diagnostic"

    @property
    def index_range(self) -> tuple[int, int]:
        """Return the inclusive automatic index range assigned to this category."""
        return _CATEGORY_RANGES[self]


_CATEGORY_RANGES = {
    ObjectCategory.TELEMETRY: (0x2000, 0x27FF),
    ObjectCategory.COMMAND: (0x2800, 0x2FFF),
    ObjectCategory.CONFIGURATION: (0x3000, 0x37FF),
    ObjectCategory.DIAGNOSTIC: (0x3800, 0x3FFF),
}


class ObjectKind(StrEnum):
    """Structural kind of an unresolved schema-v1 object."""

    VARIABLE = "variable"
    RECORD = "record"
    ARRAY = "array"


@dataclass(frozen=True, slots=True)
class SubObjectDefinition:
    """One unresolved record field."""

    key: str
    qualified_name: str
    type_name: str
    access: Access
    info: str | None = None
    explicit_subindex: int | None = None


@dataclass(frozen=True, slots=True)
class ObjectDefinition:
    """One unresolved device- or module-owned Object Dictionary entry."""

    key: str
    qualified_name: str
    category: ObjectCategory
    type_name: str
    access: Access | None
    info: str | None = None
    explicit_index: int | None = None
    fields: tuple[SubObjectDefinition, ...] = ()
    item_type: str | None = None
    length: int | None = None

    def __post_init__(self) -> None:
        """Protect the raw IR invariants expected by later resolver stages."""
        if self.type_name == "record":
            if not self.fields:
                raise ValueError("record objects require at least one field")
            if self.item_type is not None or self.length is not None:
                raise ValueError("record objects cannot define array metadata")
            return

        if self.type_name == "array":
            if self.item_type is None or self.length is None:
                raise ValueError("array objects require item_type and length")
            if self.fields:
                raise ValueError("array objects cannot define record fields")
        elif self.fields or self.item_type is not None or self.length is not None:
            raise ValueError("variable objects cannot define record or array metadata")

        if self.access is None:
            raise ValueError("variable and array objects require an access mode")

    @property
    def kind(self) -> ObjectKind:
        """Return the structural kind without exposing YAML conditionals downstream."""
        if self.type_name == "record":
            return ObjectKind.RECORD
        if self.type_name == "array":
            return ObjectKind.ARRAY
        return ObjectKind.VARIABLE
