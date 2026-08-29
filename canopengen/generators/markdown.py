"""Deterministic Markdown documentation rendering for one resolved CANopen device."""

from __future__ import annotations

from canopengen.errors import MarkdownGenerationError
from canopengen.model import (
    AddressSource,
    AllocatedObject,
    AllocatedObjectDictionary,
    AllocatedSubObject,
    DeviceDefinition,
    ObjectCategory,
    ObjectKind,
    ResolvedDataType,
    ResolvedDefinitionTypes,
    ResolvedModuleGraph,
    ResolvedObjectType,
    ResolvedPdoDefinition,
    SubObjectRole,
)


def _cell(value: str) -> str:
    """Render plain text safely inside a Markdown table cell."""
    return " ".join(value.replace("|", "\\|").split())


def _source(source: AddressSource, distance: int) -> str:
    """Format deterministic address-allocation provenance."""
    if source is AddressSource.EXPLICIT:
        return "explicit"
    if source is AddressSource.RESERVED:
        return "reserved"
    if source is AddressSource.SEQUENTIAL:
        return "sequential"
    return f"automatic (CRC32{f' + {distance} probe' if distance else ''})"


def _type(datatype: ResolvedDataType) -> str:
    """Show both primitive storage and the developer-facing custom type."""
    primitive = f"`{datatype.primitive.alias}`"
    return (
        primitive
        if datatype.custom_type_name is None
        else f"{primitive} (`{datatype.custom_type_name}`)"
    )


def _object_type(allocated: AllocatedObject, resolved: ResolvedObjectType) -> str:
    """Document an object kind using resolved, not raw, type metadata."""
    definition = allocated.definition
    if definition.kind is ObjectKind.RECORD:
        return "record"
    if definition.kind is ObjectKind.ARRAY:
        if definition.length is None or resolved.item_datatype is None:
            raise MarkdownGenerationError(f"array '{definition.qualified_name}' is incomplete")
        return f"array of {_type(resolved.item_datatype)}, length {definition.length}"
    if resolved.datatype is None:
        raise MarkdownGenerationError(
            f"variable '{definition.qualified_name}' is missing type metadata"
        )
    return _type(resolved.datatype)


def _sub_type(
    allocated: AllocatedObject, subobject: AllocatedSubObject, resolved: ResolvedObjectType
) -> ResolvedDataType:
    """Find resolved storage metadata for one concrete compound-object subentry."""
    if subobject.role is SubObjectRole.ARRAY_ELEMENT:
        if resolved.item_datatype is None:
            raise MarkdownGenerationError(
                f"array '{allocated.definition.qualified_name}' is incomplete"
            )
        return resolved.item_datatype
    field = resolved.field_by_qualified_name(subobject.qualified_name)
    if field is None:
        raise MarkdownGenerationError(
            f"record '{allocated.definition.qualified_name}' is missing "
            f"'{subobject.qualified_name}'"
        )
    return field.datatype


def _category_heading(category: ObjectCategory) -> str:
    """Map stable schema categories to reader-facing section headings."""
    return {
        ObjectCategory.TELEMETRY: "Telemetry",
        ObjectCategory.COMMAND: "Commands",
        ObjectCategory.CONFIGURATION: "Configuration",
        ObjectCategory.DIAGNOSTIC: "Diagnostics",
    }[category]


def _object_lines(allocated: AllocatedObject, resolved: ResolvedObjectType) -> list[str]:
    """Render complete technical information for one allocated OD object."""
    definition = allocated.definition
    access = definition.access.value if definition.access is not None else "n/a"
    lines = [
        f"### `{definition.key}`",
        "",
        "| Property | Value |",
        "| --- | --- |",
        f"| Qualified name | `{definition.qualified_name}` |",
        f"| Address | `0x{allocated.index:04X}:00` |",
        f"| Kind | {definition.kind.value} |",
        f"| Resolved type | {_object_type(allocated, resolved)} |",
        f"| Access | `{access}` |",
        f"| Allocation | {_source(allocated.address_source, allocated.probe_distance)} |",
    ]
    if definition.info:
        lines.extend(("", definition.info.strip()))
    entries = tuple(item for item in allocated.subobjects if item.role is not SubObjectRole.COUNT)
    if entries:
        label = "Record fields" if definition.kind is ObjectKind.RECORD else "Array elements"
        lines.extend(
            (
                "",
                f"#### {label}",
                "",
                (
                    "| Subindex | Key | Qualified name | Resolved type | Access | Allocation | "
                    "Description |"
                ),
                "| --- | --- | --- | --- | --- | --- | --- |",
            )
        )
        for entry in entries:
            lines.append(
                f"| `0x{entry.subindex:02X}` | `{entry.key}` | `{entry.qualified_name}` | "
                f"{_type(_sub_type(allocated, entry, resolved))} | `{entry.access.value}` | "
                f"{_source(entry.address_source, entry.probe_distance)} | "
                f"{_cell(entry.info or '—')} |"
            )
    return lines


def _modules_lines(graph: ResolvedModuleGraph) -> list[str]:
    """Render the dependency-first resolved module closure."""
    lines = ["## Modules", ""]
    if not graph.modules:
        return [*lines, "This device does not import reusable modules."]
    lines.extend(
        (
            "| Namespace | Module | Parameters | Dependencies | Description |",
            "| --- | --- | --- | --- | --- |",
        )
    )
    for module in graph.modules:
        params = (
            ", ".join(f"`{parameter.name}={parameter.value!r}`" for parameter in module.parameters)
            or "—"
        )
        dependencies = ", ".join(f"`{name}`" for name in module.dependencies) or "—"
        lines.append(
            f"| `{module.namespace}` | {_cell(module.definition.name)} | {params} | "
            f"{dependencies} | "
            f"{_cell(module.definition.info or '—')} |"
        )
    return lines


def _custom_type_lines(resolved_types: ResolvedDefinitionTypes) -> list[str]:
    """Render every alias/enum in the resolved visible graph."""
    lines = ["## Custom Types", ""]
    if not resolved_types.custom_types:
        return [*lines, "This device has no custom types."]
    for datatype in resolved_types.custom_types:
        lines.extend(
            (
                f"### `{datatype.qualified_name}`",
                "",
                "| Property | Value |",
                "| --- | --- |",
                f"| Kind | {'enum' if datatype.is_enum else 'alias'} |",
                f"| Declared base | `{datatype.declared_base}` |",
                f"| Resolved primitive | `{datatype.primitive.alias}` |",
                (
                    f"| Alias chain | "
                    f"{' → '.join(f'`{name}`' for name in datatype.alias_chain) or '—'} |"
                ),
            )
        )
        if datatype.enum_members:
            lines.extend(("", "| Name | Value |", "| --- | --- |"))
            lines.extend(
                f"| `{member.name}` | `{member.value}` |" for member in datatype.enum_members
            )
        lines.append("")
    return lines


def _mapping_type(
    qualified_name: str,
    dictionary: AllocatedObjectDictionary,
    resolved_types: ResolvedDefinitionTypes,
) -> ResolvedDataType | None:
    """Find documentable scalar type metadata for a resolved PDO target."""
    for allocated in dictionary.objects:
        resolved = resolved_types.object_type(allocated.definition.qualified_name)
        if resolved is None:
            continue
        if allocated.definition.qualified_name == qualified_name:
            return resolved.datatype
        for entry in allocated.subobjects:
            if entry.qualified_name == qualified_name and entry.role is not SubObjectRole.COUNT:
                return _sub_type(allocated, entry, resolved)
    return None


def _pdo_lines(
    dictionary: AllocatedObjectDictionary,
    resolved_types: ResolvedDefinitionTypes,
    pdos: tuple[ResolvedPdoDefinition, ...],
) -> list[str]:
    """Render resolved symbolic PDO mappings and known scalar payload widths."""
    lines = ["## PDO Mapping", ""]
    if not pdos:
        return [*lines, "This device declares no PDO mappings."]
    for pdo in pdos:
        rows: list[tuple[str, str, str]] = []
        total = 0
        known = True
        for reference in pdo.mapping:
            datatype = _mapping_type(reference.qualified_name, dictionary, resolved_types)
            width = datatype.primitive.bit_width if datatype is not None else None
            if width is None:
                known = False
            else:
                total += width
            rows.append(
                (
                    reference.declared_name,
                    reference.qualified_name,
                    f"{width} bits" if width else "not scalar-sized",
                )
            )
        lines.extend(
            (
                f"### `{pdo.definition.key}` ({pdo.definition.direction.value.upper()})",
                "",
                (
                    f"Declared scalar payload: "
                    f"{f'{total} bits' if known else 'not available'}. PDO encoding and "
                    "64-bit validation are handled by the PDO generation phase."
                ),
                "",
                "| Declared mapping | Resolved target | Width |",
                "| --- | --- | --- |",
            )
        )
        lines.extend(f"| `{declared}` | `{target}` | {width} |" for declared, target, width in rows)
        lines.append("")
    return lines


def generate_markdown(
    device: DeviceDefinition,
    graph: ResolvedModuleGraph,
    dictionary: AllocatedObjectDictionary,
    resolved_types: ResolvedDefinitionTypes,
    pdos: tuple[ResolvedPdoDefinition, ...],
) -> str:
    """Generate complete, deterministic English device documentation from resolved IR.

    @param device Root device metadata and description.
    @param graph Complete resolved module graph.
    @param dictionary Complete deterministic address allocation.
    @param resolved_types Graph-wide datatype resolution results.
    @param pdos Resolved PDO symbolic declarations.
    @return Markdown document ending in one newline.
    @raises MarkdownGenerationError If supplied IR does not describe the same device.
    """
    if graph.namespace != device.name or dictionary.namespace != device.name:
        raise MarkdownGenerationError("Markdown inputs must belong to the same device namespace")
    lines = [f"# {device.name}", ""]
    if device.info:
        lines.extend((device.info.strip(), ""))
    lines.extend(_modules_lines(graph))
    lines.extend(("", "## Object Dictionary", ""))
    for category in ObjectCategory:
        lines.extend((f"## {_category_heading(category)}", ""))
        entries = tuple(item for item in dictionary.objects if item.definition.category is category)
        if not entries:
            lines.append("No objects in this category.")
        for allocated in entries:
            resolved = resolved_types.object_type(allocated.definition.qualified_name)
            if resolved is None:
                raise MarkdownGenerationError(
                    f"missing type for '{allocated.definition.qualified_name}'"
                )
            lines.extend(_object_lines(allocated, resolved))
            lines.append("")
    lines.extend(_custom_type_lines(resolved_types))
    lines.append("")
    lines.extend(_pdo_lines(dictionary, resolved_types, pdos))
    return "\n".join(lines).rstrip() + "\n"
