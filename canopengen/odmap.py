"""Human-readable Object Dictionary address-map formatting."""

from __future__ import annotations

from canopengen.model import (
    AddressDiagnostic,
    AddressSource,
    AllocatedObject,
    AllocatedObjectDictionary,
    AllocatedSubObject,
    ObjectCategory,
    ObjectKind,
    SubObjectRole,
)


def _source_label(source: AddressSource, probe_distance: int) -> str:
    """Format deterministic address provenance for developer diagnostics."""
    if source is AddressSource.EXPLICIT:
        return "explicit"
    if source is AddressSource.RESERVED:
        return "reserved"
    if source is AddressSource.SEQUENTIAL:
        return "sequential"
    suffix = f"+{probe_distance}" if probe_distance else ""
    return f"auto, crc32{suffix}"


def _object_type(allocated: AllocatedObject) -> str:
    """Render unresolved variable/record/array type metadata compactly."""
    definition = allocated.definition
    if definition.kind is ObjectKind.ARRAY:
        return f"array<{definition.item_type}>[{definition.length}]"
    return definition.type_name


def _format_object_line(allocated: AllocatedObject) -> str:
    """Format an object entry at subindex zero."""
    definition = allocated.definition
    access = definition.access.value if definition.access is not None else "--"
    source = _source_label(allocated.address_source, allocated.probe_distance)
    return (
        f"0x{allocated.index:04X}:00  {definition.key:<24} "
        f"{_object_type(allocated):<24} {access:<2}  [{source}]"
    ).rstrip()


def _format_subobject_line(index: int, subobject: AllocatedSubObject) -> str:
    """Format a record field or sequential array element."""
    source = _source_label(subobject.address_source, subobject.probe_distance)
    return (
        f"0x{index:04X}:{subobject.subindex:02X}    {subobject.key:<22} "
        f"{subobject.type_name:<24} {subobject.access.value:<2}  [{source}]"
    ).rstrip()


def format_object_dictionary_map(dictionary: AllocatedObjectDictionary) -> str:
    """Render deterministic allocated objects grouped by schema-v1 category."""
    lines = [f"{dictionary.namespace} Object Dictionary", ""]
    headings = {
        ObjectCategory.TELEMETRY: "Telemetry",
        ObjectCategory.COMMAND: "Commands",
        ObjectCategory.CONFIGURATION: "Configuration",
        ObjectCategory.DIAGNOSTIC: "Diagnostics",
    }
    for category in ObjectCategory:
        lines.extend((headings[category], "-" * 72))
        category_objects = [
            allocated
            for allocated in dictionary.objects
            if allocated.definition.category is category
        ]
        if not category_objects:
            lines.append("(none)")
        for allocated in category_objects:
            lines.append(_format_object_line(allocated))
            lines.extend(
                _format_subobject_line(allocated.index, subobject)
                for subobject in allocated.subobjects
                if subobject.role is not SubObjectRole.COUNT
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def format_address_diagnostic(diagnostic: AddressDiagnostic) -> str:
    """Render the public inputs and results of one CRC32 address calculation."""
    lines = [
        f"Qualified name: {diagnostic.qualified_name}",
        f"Canonical hash key: {diagnostic.canonical_key}",
        f"CRC32: 0x{diagnostic.crc32:08X}",
        f"Category: {diagnostic.category.value}",
        f"Category range: 0x{diagnostic.range_start:04X}-0x{diagnostic.range_end:04X}",
        f"Initial slot: {diagnostic.initial_slot}",
        f"Initial CANopen index: 0x{diagnostic.initial_index:04X}",
    ]
    if diagnostic.final_index is not None:
        if diagnostic.address_source is None or diagnostic.probe_distance is None:
            raise AssertionError("final address diagnostics require source and probe metadata")
        lines.extend(
            (
                f"Final CANopen index: 0x{diagnostic.final_index:04X}",
                f"Allocation source: {diagnostic.address_source.value}",
                f"Probe distance: {diagnostic.probe_distance}",
            )
        )
    return "\n".join(lines) + "\n"
