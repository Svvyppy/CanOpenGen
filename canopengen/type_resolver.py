"""Recursive schema-v1 alias and enum resolution."""

from __future__ import annotations

from pathlib import Path

from canopengen.errors import (
    AliasCycleError,
    AmbiguousDataTypeError,
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
    ResolvedModuleGraph,
    ResolvedObjectType,
    ResolvedSubObjectType,
)

_STRUCTURAL_TYPE_NAMES = frozenset(("record", "array"))


class _TypeResolver:
    """Single-definition resolver with explicit per-run recursion state."""

    def __init__(
        self,
        source_path: Path,
        namespace: str,
        definitions: tuple[CustomTypeDefinition, ...],
    ) -> None:
        self._source_path = source_path
        self._namespace = namespace
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
            namespace=self._namespace,
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
    resolver = _TypeResolver(definition.source_path, namespace, definition.types)
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


TypeNode = tuple[str, str]


class _GraphTypeResolver:
    """Scope-aware resolver for a root definition and its imported modules."""

    def __init__(self, graph: ResolvedModuleGraph) -> None:
        self._graph = graph
        self._scopes = {
            (
                definition.name
                if isinstance(definition, DeviceDefinition)
                else definition.namespace
            ): definition
            for definition in graph.definitions
        }
        self._definitions = {
            (namespace, definition.name): definition
            for namespace, scope in self._scopes.items()
            for definition in scope.types
        }
        self._resolved: dict[TypeNode, ResolvedCustomType] = {}
        self._stack: list[TypeNode] = []

    def resolve(self) -> ResolvedDefinitionTypes:
        """Resolve every visible declaration and every aggregated object type."""
        for node in sorted(self._definitions):
            name = node[1]
            scope = self._scopes[node[0]]
            if name in PRIMITIVE_TYPES or name in _STRUCTURAL_TYPE_NAMES:
                raise ReservedTypeNameError(
                    f"{scope.source_path}: custom type '{name}' uses a reserved schema-v1 "
                    "datatype name; choose a distinct name"
                )
            self._resolve_custom(node)

        objects: list[ResolvedObjectType] = []
        for namespace, scope in self._scopes.items():
            for object_definition in scope.objects:
                if object_definition.kind is ObjectKind.RECORD:
                    fields = tuple(
                        ResolvedSubObjectType(
                            qualified_name=field.qualified_name,
                            datatype=self.resolve_reference(
                                namespace,
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
                            item_datatype=self.resolve_reference(
                                namespace,
                                object_definition.item_type,
                                context=f"array '{object_definition.qualified_name}' item_type",
                            ),
                        )
                    )
                else:
                    objects.append(
                        ResolvedObjectType(
                            qualified_name=object_definition.qualified_name,
                            datatype=self.resolve_reference(
                                namespace,
                                object_definition.type_name,
                                context=f"object '{object_definition.qualified_name}'",
                            ),
                        )
                    )

        return ResolvedDefinitionTypes(
            namespace=self._graph.namespace,
            custom_types=tuple(self._resolved[node] for node in sorted(self._resolved)),
            objects=tuple(sorted(objects, key=lambda item: item.qualified_name)),
        )

    def resolve_reference(
        self,
        owner_namespace: str,
        name: str,
        *,
        context: str,
    ) -> ResolvedDataType:
        """Resolve a primitive, local, qualified, or uniquely imported type name."""
        primitive = PRIMITIVE_TYPES.get(name)
        if primitive is not None:
            return ResolvedDataType(
                declared_name=name,
                primitive=primitive,
                custom_type_name=None,
                alias_chain=(name,),
            )
        node = self._select_custom(owner_namespace, name, context=context)
        if node is None:
            scope = self._scopes[owner_namespace]
            raise UnknownDataTypeError(
                f"{scope.source_path}: {context} references unknown datatype '{name}'; "
                "declare it locally, import its module, or use a qualified name"
            )
        return self._resolve_custom(node).as_reference(name)

    def _select_custom(
        self,
        owner_namespace: str,
        name: str,
        *,
        context: str,
    ) -> TypeNode | None:
        """Apply local-first lookup and reject ambiguous imported declarations."""
        local = (owner_namespace, name)
        if local in self._definitions:
            return local

        visible = frozenset(self._graph.visible_namespaces(owner_namespace))
        qualified_candidates = tuple(
            sorted(
                node
                for node in self._definitions
                if node[0] in visible and f"{node[0]}.{node[1]}" == name
            )
        )
        if len(qualified_candidates) > 1:
            scope = self._scopes[owner_namespace]
            raise AmbiguousDataTypeError(
                f"{scope.source_path}: {context} qualified datatype '{name}' matches multiple "
                "namespace/type boundaries; rename a dotted namespace or declaration"
            )
        if qualified_candidates:
            return qualified_candidates[0]

        candidates = tuple(
            sorted(node for node in self._definitions if node[1] == name and node[0] in visible)
        )
        if len(candidates) > 1:
            scope = self._scopes[owner_namespace]
            names = ", ".join(f"{namespace}.{local_name}" for namespace, local_name in candidates)
            raise AmbiguousDataTypeError(
                f"{scope.source_path}: {context} datatype '{name}' is ambiguous: {names}; "
                "use a qualified datatype name"
            )
        return candidates[0] if candidates else None

    def _resolve_custom(self, node: TypeNode) -> ResolvedCustomType:
        """Resolve one scoped declaration recursively with cross-module cycle checks."""
        cached = self._resolved.get(node)
        if cached is not None:
            return cached
        if node in self._stack:
            cycle_start = self._stack.index(node)
            cycle = (*self._stack[cycle_start:], node)
            scope = self._scopes[node[0]]
            chain = " -> ".join(f"{namespace}.{name}" for namespace, name in cycle)
            raise AliasCycleError(f"{scope.source_path}: custom type alias cycle: {chain}")

        namespace, name = node
        scope = self._scopes[namespace]
        definition = self._definitions[node]
        self._stack.append(node)
        base_chain: tuple[str, ...]
        base_primitive = PRIMITIVE_TYPES.get(definition.base)
        if base_primitive is not None:
            primitive = base_primitive
            base_chain = (definition.base,)
            inherited_enum: tuple[EnumMember, ...] = ()
        else:
            base_node = self._select_custom(
                namespace,
                definition.base,
                context=f"custom type '{name}' base",
            )
            if base_node is None:
                raise UnknownDataTypeError(
                    f"{scope.source_path}: custom type '{name}' has unknown base "
                    f"'{definition.base}'; declare it locally, import its module, or use a "
                    "qualified name"
                )
            base = self._resolve_custom(base_node)
            primitive = base.primitive
            base_chain = base.alias_chain
            inherited_enum = base.enum_members

        enum_members = inherited_enum
        if definition.enum_members:
            if not primitive.enum_compatible:
                raise InvalidEnumBaseError(
                    f"{scope.source_path}: enum '{name}' resolves to non-integer primitive "
                    f"'{primitive.alias}'; use int8/int16/int32/int64 or an unsigned integer"
                )
            lower, upper = primitive.integer_range or (0, -1)
            for member in definition.enum_members:
                if not lower <= member.value <= upper:
                    raise EnumValueOutOfRangeError(
                        f"{scope.source_path}: enum '{name}' member '{member.name}' value "
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
            namespace=namespace,
        )
        self._resolved[node] = resolved
        popped = self._stack.pop()
        if popped != node:
            raise AssertionError("type resolver recursion stack is inconsistent")
        return resolved


def resolve_module_graph_types(graph: ResolvedModuleGraph) -> ResolvedDefinitionTypes:
    """Resolve custom and object datatypes across one loaded module graph.

    Local declarations shadow imported declarations. Unqualified imported names must be
    unique within the owner's transitive dependency visibility; qualified names remain
    available for intentional disambiguation.

    @param graph Root definition and recursively loaded modules.
    @return Aggregated immutable datatype resolution results.
    @raises TypeResolutionError For invalid, missing, cyclic, or ambiguous datatypes.
    """
    return _GraphTypeResolver(graph).resolve()
