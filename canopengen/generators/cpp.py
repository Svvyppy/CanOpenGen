"""C++ typed Object Dictionary metadata rendered from resolved CanOpenGen IR."""

from __future__ import annotations

import re
from collections import defaultdict

from canopengen.errors import CppGenerationError
from canopengen.model import (
    AllocatedObject,
    AllocatedObjectDictionary,
    AllocatedSubObject,
    ObjectKind,
    ResolvedDataType,
    ResolvedDefinitionTypes,
    ResolvedObjectType,
    SubObjectRole,
)

_CPP_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_CPP_KEYWORDS = frozenset(
    (
        "alignas",
        "alignof",
        "and",
        "and_eq",
        "asm",
        "auto",
        "bitand",
        "bitor",
        "bool",
        "break",
        "case",
        "catch",
        "char",
        "char8_t",
        "char16_t",
        "char32_t",
        "class",
        "compl",
        "concept",
        "const",
        "consteval",
        "constexpr",
        "constinit",
        "const_cast",
        "continue",
        "co_await",
        "co_return",
        "co_yield",
        "decltype",
        "default",
        "delete",
        "do",
        "double",
        "dynamic_cast",
        "else",
        "enum",
        "explicit",
        "export",
        "extern",
        "false",
        "float",
        "for",
        "friend",
        "goto",
        "if",
        "inline",
        "int",
        "int8_t",
        "int16_t",
        "int32_t",
        "int64_t",
        "long",
        "mutable",
        "namespace",
        "new",
        "noexcept",
        "not",
        "not_eq",
        "nullptr",
        "operator",
        "or",
        "or_eq",
        "private",
        "protected",
        "public",
        "reflexpr",
        "register",
        "reinterpret_cast",
        "requires",
        "return",
        "short",
        "signed",
        "sizeof",
        "static",
        "static_assert",
        "static_cast",
        "struct",
        "switch",
        "synchronized",
        "template",
        "this",
        "thread_local",
        "throw",
        "true",
        "try",
        "typedef",
        "typeid",
        "typename",
        "union",
        "unsigned",
        "using",
        "virtual",
        "void",
        "volatile",
        "wchar_t",
        "while",
        "xor",
        "xor_eq",
    )
)
_PRIMITIVE_CPP_TYPES = {
    "bool": "bool",
    "int8": "std::int8_t",
    "int16": "std::int16_t",
    "int32": "std::int32_t",
    "int64": "std::int64_t",
    "uint8": "std::uint8_t",
    "uint16": "std::uint16_t",
    "uint32": "std::uint32_t",
    "uint64": "std::uint64_t",
    "float32": "float",
    "float64": "double",
    "string": "const char*",
    "domain": "std::byte",
}


def validate_cpp_identifier(value: str, *, description: str) -> None:
    """Reject a YAML-derived name that cannot safely become a C++ identifier."""
    if not _CPP_IDENTIFIER.fullmatch(value) or value in _CPP_KEYWORDS:
        raise CppGenerationError(f"invalid {description} '{value}': must be a valid C++ identifier")


def _pascal_case(value: str) -> str:
    """Convert a validated YAML key to a deterministic C++ type identifier."""
    validate_cpp_identifier(value, description="YAML identifier")
    parts = tuple(part for part in value.split("_") if part)
    return "".join(part[:1].upper() + part[1:] for part in parts) or value


def _enum_type_name(
    datatype: ResolvedDataType,
    resolved_types: ResolvedDefinitionTypes,
    owner_namespace: str,
) -> str:
    """Return the generated enum name associated with one resolved reference."""
    if datatype.custom_type_name is None:
        raise AssertionError("primitive datatype cannot require an enum name")
    candidates = tuple(
        custom
        for custom in resolved_types.custom_types
        if custom.is_enum
        and (
            custom.qualified_name == datatype.custom_type_name
            or custom.name == datatype.custom_type_name
        )
    )
    local_candidates = tuple(custom for custom in candidates if custom.namespace == owner_namespace)
    if len(local_candidates) == 1:
        candidates = local_candidates
    if len(candidates) != 1:
        raise CppGenerationError(
            f"cannot unambiguously render enum datatype '{datatype.custom_type_name}'"
        )
    custom = candidates[0]
    if custom.namespace == resolved_types.namespace:
        return _pascal_case(custom.name)
    return _pascal_case(custom.namespace or "") + _pascal_case(custom.name)


def _cpp_type(
    datatype: ResolvedDataType,
    resolved_types: ResolvedDefinitionTypes,
    owner_namespace: str,
) -> str:
    """Map one resolved CANopen datatype to the public C++ metadata type."""
    if datatype.is_enum:
        return _enum_type_name(datatype, resolved_types, owner_namespace)
    return _PRIMITIVE_CPP_TYPES[datatype.primitive.alias]


def _leaf_type(
    allocated: AllocatedObject,
    subobject: AllocatedSubObject | None,
    resolved: ResolvedObjectType,
) -> ResolvedDataType:
    """Obtain one variable, record field, or array element resolved datatype."""
    if subobject is None:
        if resolved.datatype is None:
            raise CppGenerationError(
                f"object '{allocated.definition.qualified_name}' is missing its resolved datatype"
            )
        return resolved.datatype
    if subobject.role is SubObjectRole.ARRAY_ELEMENT:
        if resolved.item_datatype is None:
            raise CppGenerationError(
                f"array '{allocated.definition.qualified_name}' is missing its resolved "
                "item datatype"
            )
        return resolved.item_datatype
    field = resolved.field_by_qualified_name(subobject.qualified_name)
    if field is None:
        raise CppGenerationError(
            f"record '{allocated.definition.qualified_name}' is missing field "
            f"'{subobject.qualified_name}' datatype"
        )
    return field.datatype


def _symbol_block(
    type_name: str,
    variable_name: str,
    index: int,
    subindex: int,
    datatype: ResolvedDataType,
    resolved_types: ResolvedDefinitionTypes,
    owner_namespace: str,
    *,
    indent: str,
) -> tuple[str, ...]:
    """Render one self-contained typed address tag and its inline symbol."""
    return (
        f"{indent}struct {type_name} {{",
        f"{indent}    using Type = {_cpp_type(datatype, resolved_types, owner_namespace)};",
        f"{indent}    static constexpr std::uint16_t index = 0x{index:04X};",
        f"{indent}    static constexpr std::uint8_t subindex = 0x{subindex:02X};",
        f"{indent}}};",
        "",
        f"{indent}inline constexpr {type_name} {variable_name}{{}};",
    )


def generate_cpp_symbols(
    namespace: str,
    dictionary: AllocatedObjectDictionary,
    resolved_types: ResolvedDefinitionTypes,
) -> str:
    """Generate typed symbolic C++ Object Dictionary metadata.

    The output intentionally does not depend on CANoopEn headers.  Its small tag
    types expose the resolved C++ value type and final CANopen index/subindex, while
    generic ``SetValue``/``GetValue`` helpers adapt to a CANoopEn-compatible object
    dictionary with ``SetValue`` and ``GetValue`` members.
    """
    validate_cpp_identifier(namespace, description="device filename stem")
    if dictionary.namespace != resolved_types.namespace:
        raise CppGenerationError("allocated dictionary and resolved type namespace disagree")

    objects_by_owner: dict[str, list[AllocatedObject]] = defaultdict(list)
    for allocated in dictionary.objects:
        owner, _, _ = allocated.definition.qualified_name.partition(".")
        objects_by_owner[owner].append(allocated)

    lines = [
        "// Generated by CanOpenGen. Do not edit manually.",
        "#pragma once",
        "",
        "#include <cstddef>",
        "#include <cstdint>",
        "#include <utility>",
        "",
        f"namespace {namespace} {{",
        "",
    ]
    for custom in resolved_types.custom_types:
        if not custom.is_enum:
            continue
        enum_name = (
            _pascal_case(custom.name)
            if custom.namespace == resolved_types.namespace
            else _pascal_case(custom.namespace or "") + _pascal_case(custom.name)
        )
        lines.append(f"enum class {enum_name} : {_PRIMITIVE_CPP_TYPES[custom.primitive.alias]} {{")
        lines.extend(
            f"    {_pascal_case(member.name)} = {member.value}," for member in custom.enum_members
        )
        lines.extend(("};", ""))

    lines.extend(("namespace Objects {", ""))
    for owner in sorted(objects_by_owner):
        owner_is_root = owner == dictionary.namespace
        if not owner_is_root:
            validate_cpp_identifier(owner, description="module namespace")
            lines.extend((f"namespace {_pascal_case(owner)} {{", ""))
        for allocated in sorted(
            objects_by_owner[owner], key=lambda item: item.definition.qualified_name
        ):
            definition = allocated.definition
            resolved = resolved_types.object_type(definition.qualified_name)
            if resolved is None:
                raise CppGenerationError(f"missing resolved type for '{definition.qualified_name}'")
            indent = "    " if not owner_is_root else ""
            if definition.kind is ObjectKind.VARIABLE:
                lines.extend(
                    _symbol_block(
                        _pascal_case(definition.key),
                        definition.key,
                        allocated.index,
                        0,
                        _leaf_type(allocated, None, resolved),
                        resolved_types,
                        owner,
                        indent=indent,
                    )
                )
                lines.append("")
                continue

            scope_name = _pascal_case(definition.key)
            lines.extend((f"{indent}namespace {scope_name} {{", ""))
            for subobject in allocated.subobjects:
                if subobject.role is SubObjectRole.COUNT:
                    continue
                variable_name = (
                    f"item{subobject.subindex}"
                    if subobject.role is SubObjectRole.ARRAY_ELEMENT
                    else subobject.key
                )
                lines.extend(
                    _symbol_block(
                        _pascal_case(variable_name),
                        variable_name,
                        allocated.index,
                        subobject.subindex,
                        _leaf_type(allocated, subobject, resolved),
                        resolved_types,
                        owner,
                        indent=indent + "    ",
                    )
                )
                lines.append("")
            lines.append(f"{indent}}}  // namespace {scope_name}")
            lines.append("")
        if not owner_is_root:
            lines.append(f"}}  // namespace {_pascal_case(owner)}")
            lines.append("")
    lines.extend(
        (
            "}  // namespace Objects",
            "",
            "template <typename TObjectDictionary, typename TObject>",
            "void SetValue(TObjectDictionary& dictionary, TObject, typename TObject::Type value) {",
            "    dictionary.SetValue(TObject::index, TObject::subindex, value);",
            "}",
            "",
            "template <typename TObjectDictionary, typename TObject>",
            "typename TObject::Type GetValue(TObjectDictionary& dictionary, TObject) {",
            "    return dictionary.GetValue(TObject::index, TObject::subindex);",
            "}",
            "",
            f"}}  // namespace {namespace}",
            "",
        )
    )
    return "\n".join(lines)
