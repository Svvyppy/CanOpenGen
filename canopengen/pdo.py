"""Classic CANopen PDO mapping encoding and validation from resolved IR."""

from __future__ import annotations

from canopengen.errors import PdoValidationError
from canopengen.model import (
    Access,
    AllocatedObjectDictionary,
    PdoDirection,
    PdoMappingEntry,
    ResolvedDefinitionTypes,
    ResolvedPdoDefinition,
    ResolvedPdoMapping,
    SubObjectRole,
)


def _entry_for_reference(
    pdo: ResolvedPdoDefinition,
    qualified_name: str,
    dictionary: AllocatedObjectDictionary,
    types: ResolvedDefinitionTypes,
) -> PdoMappingEntry:
    """Resolve one symbolic leaf target to its final mapping encoding inputs."""
    for allocated in dictionary.objects:
        resolved = types.object_type(allocated.definition.qualified_name)
        if resolved is None:
            continue
        if allocated.definition.qualified_name == qualified_name:
            datatype = resolved.datatype
            subindex = 0
            access = allocated.definition.access
        else:
            subobject = next(
                (entry for entry in allocated.subobjects if entry.qualified_name == qualified_name),
                None,
            )
            if subobject is None:
                continue
            if subobject.role is SubObjectRole.COUNT:
                raise PdoValidationError(f"PDO '{pdo.definition.key}' cannot map a count entry")
            if subobject.role is SubObjectRole.ARRAY_ELEMENT:
                datatype = resolved.item_datatype
            else:
                field = resolved.field_by_qualified_name(qualified_name)
                datatype = field.datatype if field is not None else None
            subindex = subobject.subindex
            access = subobject.access
        if access is None:
            raise PdoValidationError(f"PDO '{pdo.definition.key}' cannot map a container object")
        if pdo.definition.direction is PdoDirection.TRANSMIT and access is Access.WRITE_ONLY:
            raise PdoValidationError(
                f"TPDO '{pdo.definition.key}' maps write-only object '{qualified_name}'"
            )
        if pdo.definition.direction is PdoDirection.RECEIVE and access is Access.READ_ONLY:
            raise PdoValidationError(
                f"RPDO '{pdo.definition.key}' maps read-only object '{qualified_name}'"
            )
        if (
            datatype is None
            or datatype.primitive.bit_width is None
            or not datatype.primitive.pdo_mappable
        ):
            raise PdoValidationError(
                f"{pdo.definition.direction.value.upper()} '{pdo.definition.key}' maps "
                f"'{qualified_name}', whose type is not PDO-mappable"
            )
        reference = next(item for item in pdo.mapping if item.qualified_name == qualified_name)
        return PdoMappingEntry(
            reference,
            allocated.index,
            subindex,
            datatype.primitive.alias,
            datatype.primitive.bit_width,
        )
    raise PdoValidationError(
        f"PDO '{pdo.definition.key}' maps unknown allocated target '{qualified_name}'"
    )


def resolve_pdo_mappings(
    pdos: tuple[ResolvedPdoDefinition, ...],
    dictionary: AllocatedObjectDictionary,
    types: ResolvedDefinitionTypes,
) -> tuple[ResolvedPdoMapping, ...]:
    """Encode and validate all classic PDO mappings, including their 64-bit budgets."""
    resolved: list[ResolvedPdoMapping] = []
    for pdo in pdos:
        entries = tuple(
            _entry_for_reference(pdo, item.qualified_name, dictionary, types)
            for item in pdo.mapping
        )
        result = ResolvedPdoMapping(pdo.definition, entries)
        if result.total_bits > 64:
            detail = "\n".join(
                f"{entry.reference.declared_name:<24} {entry.datatype_alias:<8} "
                f"{entry.bit_width:>2} bits"
                for entry in entries
            )
            raise PdoValidationError(
                f"{pdo.definition.direction.value.upper()} '{pdo.definition.key}' exceeds maximum "
                f"payload of 64 bits ({result.total_bits} bits):\n{detail}"
            )
        resolved.append(result)
    return tuple(resolved)
