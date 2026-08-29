"""Schema-v1 YAML parsing into explicit unresolved models."""

from __future__ import annotations

import json
from collections.abc import Mapping
from functools import lru_cache
from importlib import resources
from pathlib import Path
from typing import Any, TypeAlias, cast

import yaml
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError, best_match

from canopengen.errors import ParseError, SchemaValidationError, UnsupportedSchemaVersionError
from canopengen.model import (
    Access,
    CustomTypeDefinition,
    DeviceDefinition,
    EnumMember,
    ModuleDefinition,
    ModuleImport,
    ModuleParameter,
    ObjectCategory,
    ObjectDefinition,
    ParameterValue,
    PdoDefinition,
    PdoDirection,
    SubObjectDefinition,
)

SUPPORTED_SCHEMA_VERSION = 1
Definition: TypeAlias = DeviceDefinition | ModuleDefinition
JsonObject: TypeAlias = dict[str, Any]


@lru_cache(maxsize=1)
def _schema() -> Mapping[str, Any]:
    """Load the canonical JSON Schema from a checkout or an installed wheel."""
    checkout_schema = Path(__file__).parent.parent / "schemas" / "canopengen.schema.json"
    try:
        schema_text = checkout_schema.read_text(encoding="utf-8")
    except FileNotFoundError:
        schema_resource = resources.files("canopengen").joinpath(
            "schemas", "canopengen.schema.json"
        )
        schema_text = schema_resource.read_text(encoding="utf-8")

    schema = cast(JsonObject, json.loads(schema_text))
    Draft202012Validator.check_schema(schema)
    return schema


@lru_cache(maxsize=1)
def _validator() -> Draft202012Validator:
    """Construct and cache the immutable schema-v1 validator."""
    return Draft202012Validator(_schema())


def _load_yaml(path: Path) -> JsonObject:
    """Read one YAML mapping and normalize YAML-library errors."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as error:
        raise ParseError(path, f"cannot read YAML file: {error.strerror or error}") from error

    try:
        document: object = yaml.safe_load(text)
    except yaml.MarkedYAMLError as error:
        line = error.problem_mark.line + 1 if error.problem_mark is not None else None
        detail = error.problem or "malformed YAML"
        raise ParseError(path, detail, line=line) from error
    except yaml.YAMLError as error:
        raise ParseError(path, f"malformed YAML: {error}") from error

    if not isinstance(document, dict):
        raise SchemaValidationError(path, "", "document root must be a mapping")
    return cast(JsonObject, document)


def _format_error_path(error: ValidationError) -> str:
    """Render a jsonschema path as a familiar dotted YAML path."""
    parts: list[str] = []
    for component in error.absolute_path:
        if isinstance(component, int):
            if parts:
                parts[-1] = f"{parts[-1]}[{component}]"
            else:
                parts.append(f"[{component}]")
        else:
            parts.append(str(component))
    return ".".join(parts)


def _reject_non_string_keys(path: Path, value: object, *, field_path: str = "") -> None:
    """Reject YAML-only mapping keys that cannot be represented by JSON Schema."""
    if isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str):
                raise SchemaValidationError(
                    path,
                    field_path,
                    f"mapping keys must be strings; got {key!r}",
                )
            child_path = f"{field_path}.{key}" if field_path else key
            _reject_non_string_keys(path, child, field_path=child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            child_path = f"{field_path}[{index}]" if field_path else f"[{index}]"
            _reject_non_string_keys(path, child, field_path=child_path)


def _validate_structure(path: Path, document: JsonObject) -> None:
    """Validate schema version first, then all other public structural rules."""
    _reject_non_string_keys(path, document)
    version = document.get("schema")
    if version != SUPPORTED_SCHEMA_VERSION:
        raise UnsupportedSchemaVersionError(path, version)

    error = best_match(_validator().iter_errors(document))
    if error is not None:
        raise SchemaValidationError(path, _format_error_path(error), error.message)


def _as_mapping(value: object) -> JsonObject:
    """Narrow a mapping already proven valid by JSON Schema."""
    if not isinstance(value, dict):
        raise AssertionError("schema-validated mapping has an unexpected runtime type")
    return cast(JsonObject, value)


def _as_optional_info(value: object) -> str | None:
    """Narrow optional info already proven valid by JSON Schema."""
    if value is None or isinstance(value, str):
        return value
    raise AssertionError("schema-validated info has an unexpected runtime type")


def _as_parameter(value: object) -> ParameterValue:
    """Narrow a module parameter to the intentionally small scalar value set."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise AssertionError("schema-validated parameter has an unexpected runtime type")


def _parse_imports(raw_imports: object) -> tuple[ModuleImport, ...]:
    """Parse simple and parameterized imports without resolving dependencies."""
    if raw_imports is None:
        return ()
    if not isinstance(raw_imports, list):
        raise AssertionError("schema-validated modules has an unexpected runtime type")

    imports: list[ModuleImport] = []
    for raw_import in raw_imports:
        if isinstance(raw_import, str):
            imports.append(ModuleImport(name=raw_import))
            continue

        import_data = _as_mapping(raw_import)
        params_data = _as_mapping(import_data.get("params", {}))
        parameters = tuple(
            ModuleParameter(name=name, value=_as_parameter(params_data[name]))
            for name in sorted(params_data)
        )
        imports.append(ModuleImport(name=cast(str, import_data["name"]), parameters=parameters))
    return tuple(imports)


def _parse_types(raw_types: object) -> tuple[CustomTypeDefinition, ...]:
    """Parse aliases and enum declarations while leaving base resolution deferred."""
    types_data = _as_mapping(raw_types or {})
    definitions: list[CustomTypeDefinition] = []
    for name in sorted(types_data):
        type_data = _as_mapping(types_data[name])
        enum_data = _as_mapping(type_data.get("enum", {}))
        members = tuple(
            EnumMember(name=member_name, value=cast(int, enum_data[member_name]))
            for member_name in sorted(enum_data)
        )
        definitions.append(
            CustomTypeDefinition(
                name=name,
                base=cast(str, type_data["base"]),
                enum_members=members,
            )
        )
    return tuple(definitions)


def _parse_fields(
    raw_fields: object,
    *,
    parent_qualified_name: str,
) -> tuple[SubObjectDefinition, ...]:
    """Parse record fields and assign deterministic qualified names."""
    fields_data = _as_mapping(raw_fields)
    fields: list[SubObjectDefinition] = []
    for key in sorted(fields_data):
        field_data = _as_mapping(fields_data[key])
        fields.append(
            SubObjectDefinition(
                key=key,
                qualified_name=f"{parent_qualified_name}.{key}",
                type_name=cast(str, field_data["type"]),
                access=Access(cast(str, field_data["access"])),
                info=_as_optional_info(field_data.get("info")),
                explicit_subindex=cast(int | None, field_data.get("subindex")),
            )
        )
    return tuple(fields)


def _parse_objects(raw_objects: object, *, namespace: str) -> tuple[ObjectDefinition, ...]:
    """Parse variables, records, and arrays into normalized raw objects."""
    objects_data = _as_mapping(raw_objects or {})
    objects: list[ObjectDefinition] = []
    for key in sorted(objects_data):
        object_data = _as_mapping(objects_data[key])
        type_name = cast(str, object_data["type"])
        qualified_name = f"{namespace}.{key}"
        raw_access = object_data.get("access")
        access = Access(cast(str, raw_access)) if raw_access is not None else None
        fields = (
            _parse_fields(object_data["fields"], parent_qualified_name=qualified_name)
            if type_name == "record"
            else ()
        )
        objects.append(
            ObjectDefinition(
                key=key,
                qualified_name=qualified_name,
                category=ObjectCategory(cast(str, object_data["category"])),
                type_name=type_name,
                access=access,
                info=_as_optional_info(object_data.get("info")),
                explicit_index=cast(int | None, object_data.get("index")),
                fields=fields,
                item_type=cast(str | None, object_data.get("item_type")),
                length=cast(int | None, object_data.get("length")),
            )
        )
    return tuple(objects)


def _parse_pdos(raw_pdo: object, *, namespace: str) -> tuple[PdoDefinition, ...]:
    """Parse symbolic TPDO/RPDO mappings without resolving object references."""
    if raw_pdo is None:
        return ()
    pdo_data = _as_mapping(raw_pdo)
    definitions: list[PdoDefinition] = []
    for direction in PdoDirection:
        group_data = _as_mapping(pdo_data.get(direction.value, {}))
        for key in sorted(group_data):
            definition_data = _as_mapping(group_data[key])
            raw_mapping = definition_data["mapping"]
            if not isinstance(raw_mapping, list):
                raise AssertionError("schema-validated PDO mapping has an unexpected runtime type")
            definitions.append(
                PdoDefinition(
                    key=key,
                    owner_namespace=namespace,
                    direction=direction,
                    mapping=tuple(cast(list[str], raw_mapping)),
                )
            )
    return tuple(definitions)


def _parse_device(path: Path, document: JsonObject) -> DeviceDefinition:
    """Convert a structurally valid device mapping to the raw device IR."""
    metadata = _as_mapping(document["device"])
    name = cast(str, metadata["name"])
    return DeviceDefinition(
        schema_version=SUPPORTED_SCHEMA_VERSION,
        name=name,
        source_path=path,
        info=_as_optional_info(metadata.get("info")),
        imports=_parse_imports(document.get("modules")),
        types=_parse_types(document.get("types")),
        objects=_parse_objects(document.get("objects"), namespace=name),
        pdos=_parse_pdos(document.get("pdo"), namespace=name),
    )


def _parse_module(path: Path, document: JsonObject) -> ModuleDefinition:
    """Convert a structurally valid module mapping to the raw module IR."""
    metadata = _as_mapping(document["module"])
    namespace = path.stem
    return ModuleDefinition(
        schema_version=SUPPORTED_SCHEMA_VERSION,
        namespace=namespace,
        name=cast(str, metadata["name"]),
        source_path=path,
        info=_as_optional_info(metadata.get("info")),
        imports=_parse_imports(document.get("modules")),
        types=_parse_types(document.get("types")),
        objects=_parse_objects(document.get("objects"), namespace=namespace),
        pdos=_parse_pdos(document.get("pdo"), namespace=namespace),
    )


def parse_definition(path: str | Path) -> Definition:
    """Parse one schema-v1 Device or Module YAML file into unresolved models.

    @param path Source YAML path.
    @return A structurally validated raw device or module definition.
    @raises ParseError If the file cannot be read or decoded as YAML.
    @raises UnsupportedSchemaVersionError If ``schema`` is absent or unsupported.
    @raises SchemaValidationError If the YAML shape violates schema v1.
    """
    source_path = Path(path)
    document = _load_yaml(source_path)
    _validate_structure(source_path, document)
    if "device" in document:
        return _parse_device(source_path, document)
    return _parse_module(source_path, document)


def parse_device(path: str | Path) -> DeviceDefinition:
    """Parse a Device YAML file and reject a structurally valid Module file."""
    source_path = Path(path)
    definition = parse_definition(source_path)
    if not isinstance(definition, DeviceDefinition):
        raise SchemaValidationError(source_path, "module", "expected a Device YAML file")
    return definition


def parse_module(path: str | Path) -> ModuleDefinition:
    """Parse a Module YAML file and reject a structurally valid Device file."""
    source_path = Path(path)
    definition = parse_definition(source_path)
    if not isinstance(definition, ModuleDefinition):
        raise SchemaValidationError(source_path, "device", "expected a Module YAML file")
    return definition
