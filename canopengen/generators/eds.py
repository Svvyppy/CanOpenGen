"""CiA 306 EDS rendering compatible with the bundled CANoopEn Eds2Od tool."""

from __future__ import annotations

from canopengen.errors import EdsGenerationError
from canopengen.model import (
    PRIMITIVE_TYPES,
    Access,
    AllocatedObject,
    AllocatedObjectDictionary,
    AllocatedSubObject,
    ObjectKind,
    PrimitiveDataType,
    ResolvedDataType,
    ResolvedDefinitionTypes,
    ResolvedObjectType,
    SubObjectRole,
)

_EDS_ACCESS: dict[Access, str] = {
    Access.READ_ONLY: "ro",
    Access.WRITE_ONLY: "wo",
    Access.READ_WRITE: "rw",
}


def _escape_value(value: str) -> str:
    """Render an INI field as one line accepted by Eds2Od's minimalist parser."""
    return " ".join(value.replace("\r", " ").replace("\n", " ").split())


def _section(name: str, fields: tuple[tuple[str, str], ...]) -> str:
    """Render one deterministic EDS INI section."""
    lines = [f"[{name}]", *(f"{key}={_escape_value(value)}" for key, value in fields)]
    return "\n".join(lines)


def _datatype_fields(
    parameter_name: str,
    datatype: PrimitiveDataType,
    access: Access,
    *,
    default_value: int | None = None,
) -> tuple[tuple[str, str], ...]:
    """Return the leaf fields that Eds2Od reads for a VAR or subobject section."""
    fields: list[tuple[str, str]] = [
        ("ParameterName", parameter_name),
        ("ObjectType", "0x7"),
        ("DataType", f"0x{datatype.eds_data_type:04X}"),
        ("AccessType", _EDS_ACCESS[access]),
    ]
    if default_value is not None:
        fields.append(("DefaultValue", str(default_value)))
    fields.append(("PDOMapping", "0"))
    return tuple(fields)


def _object_datatype(
    allocated: AllocatedObject,
    resolved: ResolvedObjectType,
) -> ResolvedDataType:
    """Return the resolved storage type for a variable object."""
    if allocated.definition.kind is not ObjectKind.VARIABLE or resolved.datatype is None:
        raise EdsGenerationError(
            f"object '{allocated.definition.qualified_name}' is missing resolved variable type"
        )
    return resolved.datatype


def _subobject_datatype(
    allocated: AllocatedObject,
    subobject: AllocatedSubObject,
    resolved: ResolvedObjectType,
) -> PrimitiveDataType:
    """Return the storage primitive for a container count, field, or array element."""
    if subobject.role is SubObjectRole.COUNT:
        return PRIMITIVE_TYPES["uint8"]
    if subobject.role is SubObjectRole.ARRAY_ELEMENT:
        if resolved.item_datatype is None:
            raise EdsGenerationError(
                f"array '{allocated.definition.qualified_name}' is missing its resolved item type"
            )
        return resolved.item_datatype.primitive
    field = resolved.field_by_qualified_name(subobject.qualified_name)
    if field is None:
        raise EdsGenerationError(
            f"record '{allocated.definition.qualified_name}' is missing resolved field "
            f"'{subobject.qualified_name}'"
        )
    return field.datatype.primitive


def _container_sections(
    allocated: AllocatedObject,
    resolved: ResolvedObjectType,
) -> tuple[str, ...]:
    """Render an Eds2Od-recognized ARRAY/RECORD container and all leaf subentries."""
    definition = allocated.definition
    object_type = "0x8" if definition.kind is ObjectKind.ARRAY else "0x9"
    sections = [
        _section(
            f"{allocated.index:04X}",
            (
                ("ParameterName", definition.qualified_name),
                ("ObjectType", object_type),
                ("SubNumber", str(len(allocated.subobjects))),
            ),
        )
    ]
    for subobject in allocated.subobjects:
        parameter_name = (
            "Number of Entries" if subobject.role is SubObjectRole.COUNT else subobject.key
        )
        sections.append(
            _section(
                f"{allocated.index:04X}sub{subobject.subindex:X}",
                _datatype_fields(
                    parameter_name,
                    _subobject_datatype(allocated, subobject, resolved),
                    subobject.access,
                    default_value=subobject.default_value,
                ),
            )
        )
    return tuple(sections)


def _object_sections(
    allocated: AllocatedObject,
    resolved_types: ResolvedDefinitionTypes,
) -> tuple[str, ...]:
    """Render one allocated object using its graph-wide type resolution metadata."""
    resolved = resolved_types.object_type(allocated.definition.qualified_name)
    if resolved is None:
        raise EdsGenerationError(
            f"missing resolved type for '{allocated.definition.qualified_name}'"
        )
    if allocated.definition.kind is not ObjectKind.VARIABLE:
        return _container_sections(allocated, resolved)
    datatype = _object_datatype(allocated, resolved)
    if allocated.definition.access is None:
        raise EdsGenerationError(
            f"variable '{allocated.definition.qualified_name}' is missing access metadata"
        )
    return (
        _section(
            f"{allocated.index:04X}",
            _datatype_fields(
                allocated.definition.qualified_name,
                datatype.primitive,
                allocated.definition.access,
            ),
        ),
    )


def generate_eds(
    device_name: str,
    dictionary: AllocatedObjectDictionary,
    resolved_types: ResolvedDefinitionTypes,
) -> str:
    """Generate one deterministic CiA 306 EDS document from fully resolved IR.

    The bundled Eds2Od reads leaf ``[INDEX]`` and ``[INDEXsubN]`` sections directly;
    this renderer emits every application entry with the exact CiA 306 datatype codes
    and access spellings that its parser/code generator accepts.

    @param device_name Device identity used for EDS metadata and file naming.
    @param dictionary Fully allocated complete Device Object Dictionary.
    @param resolved_types Graph-wide datatype resolution results.
    @return UTF-8 EDS text ending in one newline.
    @raises EdsGenerationError If resolved/allocated IR invariants are incomplete.
    """
    if dictionary.namespace != device_name:
        raise EdsGenerationError(
            f"EDS device '{device_name}' does not match allocation namespace "
            f"'{dictionary.namespace}'"
        )
    indexes = tuple(sorted(allocated.index for allocated in dictionary.objects))
    manufacturer_fields = (
        ("SupportedObjects", str(len(indexes))),
        *((str(position), f"0x{index:04X}") for position, index in enumerate(indexes, start=1)),
    )
    sections = [
        _section(
            "FileInfo",
            (
                ("FileName", f"{device_name}.eds"),
                ("FileVersion", "1"),
                ("FileRevision", "1"),
                ("EDSVersion", "4.0"),
            ),
        ),
        _section(
            "DeviceInfo",
            (
                ("VendorName", "CanOpenGen"),
                ("VendorNumber", "0x00000000"),
                ("ProductName", device_name),
                ("ProductNumber", "0x00000000"),
                ("RevisionNumber", "0x00000001"),
                ("SimpleBootUpMaster", "0"),
                ("SimpleBootUpSlave", "1"),
                ("Granularity", "8"),
                ("DynamicChannelsSupported", "0"),
                ("CompactPDO", "0"),
                ("GroupMessaging", "0"),
                ("NrOfRXPDO", "0"),
                ("NrOfTXPDO", "0"),
                ("LSS_Supported", "0"),
            ),
        ),
        _section("MandatoryObjects", (("SupportedObjects", "0"),)),
        _section("OptionalObjects", (("SupportedObjects", "0"),)),
        _section("ManufacturerObjects", manufacturer_fields),
    ]
    for allocated in dictionary.objects:
        sections.extend(_object_sections(allocated, resolved_types))
    return "\n\n".join(sections) + "\n"
