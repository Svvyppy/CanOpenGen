"""Recursive schema-v1 alias and enum resolution."""

from __future__ import annotations

from pathlib import Path

from canopengen.errors import (
    AliasCycleError,
    EnumValueOutOfRangeError,
    InvalidEnumBaseError,
    ReservedTypeNameError,
    UnknownDataTypeError,
)
from canopengen.model import (
    PRIMITIVE_TYPES,
    CustomTypeDefinition,
    DeviceDefinition,
    EnumMember,
    ModuleDefinition,
    ObjectKind,
    ResolvedCustomType,
    ResolvedDataType,
    ResolvedDefinitionTypes,
    ResolvedObjectType,
    ResolvedSubObjectType,
)

_STRUCTURAL_TYPE_NAMES = frozenset(("record", "array"))


class _TypeResolver:
    """Single-definition resolver with explicit per-run recursion state."""

    def __init__(
        self,
        source_path: Path,
        definitions: tuple[CustomTypeDefinition, ...],
    ) -> None:
        self._source_path = source_path
        self._definitions = {definition.name: definition for definition in definitions}
        self._resolved: dict[str, ResolvedCustomType] = {}
        self._stack: list[str] = []

    def resolve_all(self) -> tuple[ResolvedCustomType, ...]:
        """Resolve every declaration, including currently unused aliases."""
        for name in sorted(self._definitions):
            if name in PRIMITIVE_TYPES or name in _STRUCTURAL_TYPE_NAMES:
                raise ReservedTypeNameError(
                    f"{self._source_path}: custom type '{name}' uses a reserved schema-v1 "
                    "datatype name; choose a distinct name"
                )
            self._resolve_custom(name)
        return tuple(self._resolved[name] for name in sorted(self._resolved))

    def resolve_reference(self, name: str, *, context: str) -> ResolvedDataType:
        """Resolve a primitive/custom reference with contextual diagnostics."""
        primitive = PRIMITIVE_TYPES.get(name)
        if primitive is not None:
            return ResolvedDataType(
                declared_name=name,
                primitive=primitive,
                custom_type_name=None,
                alias_chain=(name,),
            )
        if name in self._definitions:
            return self._resolve_custom(name).as_reference()
        raise UnknownDataTypeError(
            f"{self._source_path}: {context} references unknown datatype '{name}'; "
            "declare it under 'types' or use a supported primitive alias"
        )

    def _resolve_custom(self, name: str) -> ResolvedCustomType:
        """Resolve one declaration recursively with complete cycle reporting."""
        cached = self._resolved.get(name)
        if cached is not None:
            return cached
        if name in self._stack:
            cycle_start = self._stack.index(name)
            cycle = (*self._stack[cycle_start:], name)
            raise AliasCycleError(
                f"{self._source_path}: custom type alias cycle: {' -> '.join(cycle)}"
            )

        definition = self._definitions[name]
        self._stack.append(name)
        base_chain: tuple[str, ...]
        inherited_enum: tuple[EnumMember, ...]
        base_primitive = PRIMITIVE_TYPES.get(definition.base)
        if base_primitive is not None:
            primitive = base_primitive
            base_chain = (definition.base,)
            inherited_enum = ()
        elif definition.base in self._definitions:
            base = self._resolve_custom(definition.base)
            primitive = base.primitive
            base_chain = base.alias_chain
            inherited_enum = base.enum_members
        else:
            raise UnknownDataTypeError(
                f"{self._source_path}: custom type '{name}' has unknown base '{definition.base}'"
            )

        enum_members = inherited_enum
        if definition.enum_members:
            if not primitive.enum_compatible:
                raise InvalidEnumBaseError(
                    f"{self._source_path}: enum '{name}' resolves to non-integer primitive "
                    f"'{primitive.alias}'; use int8/int16/int32/int64 or an unsigned integer"
                )
            lower, upper = primitive.integer_range or (0, -1)
            for member in definition.enum_members:
                if not lower <= member.value <= upper:
                    raise EnumValueOutOfRangeError(
                        f"{self._source_path}: enum '{name}' member '{member.name}' value "
                        f"{member.value} is outside {primitive.alias} range {lower}..{upper}"
                    )
            enum_members = tuple(
                sorted(definition.enum_members, key=lambda member: (member.value, member.name))
            )

        resolved = ResolvedCustomType(
            name=name,
            declared_base=definition.base,
            primitive=primitive,
            alias_chain=(name, *base_chain),
            enum_members=enum_members,
        )
        self._resolved[name] = resolved
        popped = self._stack.pop()
        if popped != name:
            raise AssertionError("type resolver recursion stack is inconsistent")
        return resolved


def resolve_definition_types(
    definition: DeviceDefinition | ModuleDefinition,
) -> ResolvedDefinitionTypes:
    """Resolve all custom and object datatypes in one parsed definition.

    @param definition Structurally valid raw Device or Module definition.
    @return Immutable custom/object type-resolution result.
    @raises TypeResolutionError For unknown names, cycles, invalid enum bases, or range.
    """
    namespace = (
        definition.name if isinstance(definition, DeviceDefinition) else definition.namespace
    )
    resolver = _TypeResolver(definition.source_path, definition.types)
    custom_types = resolver.resolve_all()
    objects: list[ResolvedObjectType] = []
    for object_definition in definition.objects:
        if object_definition.kind is ObjectKind.RECORD:
            fields = tuple(
                ResolvedSubObjectType(
                    qualified_name=field.qualified_name,
                    datatype=resolver.resolve_reference(
                        field.type_name,
                        context=f"record field '{field.qualified_name}'",
                    ),
                )
                for field in object_definition.fields
            )
            objects.append(
                ResolvedObjectType(
                    qualified_name=object_definition.qualified_name,
                    fields=fields,
                )
            )
        elif object_definition.kind is ObjectKind.ARRAY:
            if object_definition.item_type is None:
                raise AssertionError("schema-validated array is missing item_type")
            objects.append(
                ResolvedObjectType(
                    qualified_name=object_definition.qualified_name,
                    item_datatype=resolver.resolve_reference(
                        object_definition.item_type,
                        context=f"array '{object_definition.qualified_name}' item_type",
                    ),
                )
            )
        else:
            objects.append(
                ResolvedObjectType(
                    qualified_name=object_definition.qualified_name,
                    datatype=resolver.resolve_reference(
                        object_definition.type_name,
                        context=f"object '{object_definition.qualified_name}'",
                    ),
                )
            )
    return ResolvedDefinitionTypes(
        namespace=namespace,
        custom_types=custom_types,
        objects=tuple(objects),
    )
