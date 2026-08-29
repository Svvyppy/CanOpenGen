# Architecture

CanOpenGen uses explicit stages so YAML parsing, semantic behavior, allocation, and
output formats do not leak into one another:

```text
YAML -> raw models -> module resolver -> type resolver
     -> allocator -> validator -> resolved IR -> generators
```

Generators consume only resolved and validated internal representations. The EDS
backend feeds Eds2Od; it does not produce CANoopEn C++ itself.

## Phase 1 raw IR

The YAML parser emits frozen dataclasses rather than exposing YAML dictionaries:

```text
DeviceDefinition / ModuleDefinition
├── ModuleImport[]
│   └── ModuleParameter[]
├── CustomTypeDefinition[]
│   └── EnumMember[]
├── ObjectDefinition[]
│   └── SubObjectDefinition[]
└── PdoDefinition[]
```

`ObjectDefinition` holds the YAML type name, category, optional explicit index,
qualified name, and exactly one valid variable/record/array shape. Record fields retain
explicit subindices. `PdoDefinition` preserves symbolic mapping order.

Primitive aliases and their CANopen names, widths, integer ranges, and PDO-mappability
live in one registry. Numeric EDS datatype identifiers are intentionally deferred until
the bundled Eds2Od source is inspected.

The raw IR is structurally valid but unresolved. It intentionally contains module
names, custom base names, symbolic references, and absent automatic addresses. Later
stages produce new resolved models instead of mutating YAML dictionaries.
