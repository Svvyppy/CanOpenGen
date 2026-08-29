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

## Phase 4 module graph

The module resolver recursively loads `Modules/<namespace>.yml` and produces:

```text
ResolvedModuleGraph
├── root: DeviceDefinition | ModuleDefinition
├── root_dependencies[]
└── ResolvedModule[]
    ├── ModuleDefinition
    ├── parameters[]
    └── dependencies[]
```

The module tuple is dependency-first and contains each equally configured transitive
module once. DFS state reports a complete dependency cycle; a separate configuration
registry rejects one namespace reached with different scalar parameters. Direct
duplicate imports fail instead of being silently normalized.

`ResolvedModuleGraph` exposes the combined object/PDO inputs and each owner's transitive
visibility. `ResolvedPdoDefinition` replaces every local, imported, or explicit
qualified mapping name with a `ResolvedObjectReference`. Unknown and ambiguous names
fail before generator phases.

## Phase 3/4 type IR

The type resolver recursively lowers each local type reference without changing raw
definitions:

```text
ResolvedDefinitionTypes
├── ResolvedCustomType[]
│   └── primitive / alias_chain / enum_members
└── ResolvedObjectType[]
    ├── ResolvedDataType
    ├── item_datatype
    └── ResolvedSubObjectType[]
```

Every `ResolvedDataType` records its declared name, resolved primitive, applicable
custom type name, complete alias chain, and inherited/declared enum semantics. A
per-run recursion stack reports exact cycles without global mutable resolver state.

The graph-aware resolver builds one declaration table keyed by `(namespace, local
name)`. Local declarations shadow imports; imported unqualified names must be unique;
explicit qualified names remain selectable. Cross-module aliases use the same enum,
range, and cycle rules as device-local aliases.

## Phase 2 address IR

The allocator pairs raw definitions with immutable address metadata:

```text
AllocatedObjectDictionary
└── AllocatedObject[]
    ├── ObjectDefinition
    ├── index / AddressSource / probe_distance
    └── AllocatedSubObject[]
        └── subindex / role / AddressSource / probe_distance
```

Explicit indexes/subindices are validated and reserved before automatic allocation.
CRC32 helpers expose canonicalization separately from probing so the `address` command
and compatibility tests use the same implementation. Arrays produce reserved count and
sequential element entries; records produce reserved count and allocated field entries.

Phase 2 operates on a supplied complete object sequence and has no module-loading
knowledge. The CLI passes the Phase 4 graph's complete transitive object set into the
same allocator.
