"""Immutable datatype-resolution results."""

from __future__ import annotations

from dataclasses import dataclass

from canopengen.model.datatype import EnumMember, PrimitiveDataType


@dataclass(frozen=True, slots=True)
class ResolvedDataType:
    """A type reference lowered to one standard CANopen primitive."""

    declared_name: str
    primitive: PrimitiveDataType
    custom_type_name: str | None
    alias_chain: tuple[str, ...]
    enum_members: tuple[EnumMember, ...] = ()

    @property
    def is_enum(self) -> bool:
        """Return whether the reference carries enum semantics."""
        return bool(self.enum_members)


@dataclass(frozen=True, slots=True)
class ResolvedCustomType:
    """One alias/enum declaration after recursive base resolution."""

    name: str
    declared_base: str
    primitive: PrimitiveDataType
    alias_chain: tuple[str, ...]
    enum_members: tuple[EnumMember, ...] = ()
    namespace: str | None = None

    @property
    def qualified_name(self) -> str:
        """Return the namespace-qualified declaration identity when available."""
        if self.namespace is None:
            return self.name
        return f"{self.namespace}.{self.name}"

    @property
    def is_enum(self) -> bool:
        """Return whether this declaration owns or inherits enum semantics."""
        return bool(self.enum_members)

    def as_reference(self, declared_name: str | None = None) -> ResolvedDataType:
        """Create resolved metadata for an object that names this custom type."""
        reference_name = declared_name or self.name
        return ResolvedDataType(
            declared_name=reference_name,
            primitive=self.primitive,
            custom_type_name=reference_name,
            alias_chain=self.alias_chain,
            enum_members=self.enum_members,
        )


@dataclass(frozen=True, slots=True)
class ResolvedSubObjectType:
    """Resolved datatype metadata for one record field."""

    qualified_name: str
    datatype: ResolvedDataType


@dataclass(frozen=True, slots=True)
class ResolvedObjectType:
    """Resolved variable, record-field, or array-item datatype metadata."""

    qualified_name: str
    datatype: ResolvedDataType | None = None
    item_datatype: ResolvedDataType | None = None
    fields: tuple[ResolvedSubObjectType, ...] = ()

    def field_by_qualified_name(self, qualified_name: str) -> ResolvedSubObjectType | None:
        """Return record-field type metadata by deterministic identity."""
        return next(
            (field for field in self.fields if field.qualified_name == qualified_name),
            None,
        )


@dataclass(frozen=True, slots=True)
class ResolvedDefinitionTypes:
    """All custom and object datatype results for one definition namespace."""

    namespace: str
    custom_types: tuple[ResolvedCustomType, ...]
    objects: tuple[ResolvedObjectType, ...]

    def custom_type(self, name: str) -> ResolvedCustomType | None:
        """Return a resolved custom declaration by qualified or unambiguous local name."""
        qualified = next(
            (datatype for datatype in self.custom_types if datatype.qualified_name == name),
            None,
        )
        if qualified is not None:
            return qualified
        local = tuple(datatype for datatype in self.custom_types if datatype.name == name)
        if len(local) == 1:
            return local[0]
        owned = tuple(datatype for datatype in local if datatype.namespace == self.namespace)
        return owned[0] if len(owned) == 1 else None

    def object_type(self, qualified_name: str) -> ResolvedObjectType | None:
        """Return resolved object metadata by qualified name."""
        return next(
            (datatype for datatype in self.objects if datatype.qualified_name == qualified_name),
            None,
        )
