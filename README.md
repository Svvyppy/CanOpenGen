# CanOpenGen

CanOpenGen is an open-source, declarative CANopen Object Dictionary generator for
embedded projects using the CANoopEn C++ stack. A versioned YAML description will
become the single source of truth for validation, deterministic address allocation,
EDS generation, Markdown documentation, and CANoopEn C++ generation through Eds2Od.

> [!NOTE]
> Phase 6 provides schema-v1 parsing, recursive module/type/reference resolution,
> deterministic complete-device allocation, CiA 306 EDS generation, and CANoopEn C++
> Object Dictionary generation through Eds2Od, plus complete resolved-device Markdown
> documentation. PDO payload generation remains a separate later phase.

## Planned pipeline

```text
Device YAML + reusable modules
              |
              v
parser -> resolver -> allocator -> validator -> resolved IR
                                                   |
                                      +------------+------------+
                                      |                         |
                                     EDS                    Markdown
                                      |
                                    Eds2Od
                                      |
                               CANoopEn C++ Object Dictionary
```

YAML remains the source of truth. Generated artifacts belong in the build tree;
CanOpenGen does not use persistent address lock files and does not generate CANoopEn
C++ directly.

## Development setup

CanOpenGen targets Linux and Python 3.11 or newer. Create a virtual environment and
install the development tools:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
git submodule update --init --recursive
```

Run the bootstrap checks with:

```bash
ruff format --check .
ruff check .
mypy
pytest
cmake -S . -B build
cmake --build build --target docs
```

## Validation and address maps

Every definition starts with `schema: 1` and contains exactly one `device` or `module`
identity. The current CLI validates YAML syntax, the public JSON Schema, recursive
module dependencies, aliases, enums, symbolic references, manual addresses, and
deterministic automatic allocation:

```bash
canopengen validate Device/PressureSensor.yml
canopengen validate-all
canopengen map Device/PressureSensor.yml
canopengen generate Device/PressureSensor.yml --output build/canopen
```

The example project demonstrates nested imports, equal transitive dependency
deduplication, scalar parameter plumbing, imported aliases, enums, variables, a record,
an array, manual addresses, and local/qualified TPDO/RPDO references. The map includes
the complete transitive module object set. PDO bit-width and direction validation stay
in the dedicated PDO phase.

## EDS and CANoopEn output

`generate` consumes only the fully resolved and allocated Object Dictionary. It writes
`<device>.eds` and `<device>.md`, then invokes the bundled CANoopEnTools `Eds2Od` to write
`<device>Od.hpp` and `<device>Od.cpp` under the supplied output directory:

```bash
canopengen generate Device/PressureSensor.yml --output build/canopen
```

The EDS backend uses CiA 306 numeric types and the exact Eds2Od leaf-section contract:
variables use `[INDEX]`; records and arrays use a container plus `[INDEXsubN]` entries.
Aliases and enums lower to their standard storage primitive. The repository contains a
golden EDS and CI requires the real bundled tool to accept the reference device.
The bundled source project requires .NET SDK 10 when a native Eds2Od release binary is
not present.

The Markdown document is generated from the same resolved Object Dictionary. It records
the module graph, every object and subobject address, resolved/custom types, access,
allocation provenance, descriptions, enum values, and resolved PDO mappings.

The public IDE schema is [schemas/canopengen.schema.json](schemas/canopengen.schema.json).

## Custom types

Aliases resolve recursively until they reach a standard CANopen primitive:

```yaml
types:
  RawPressure:
    base: uint32
  Pressure:
    base: RawPressure
```

Cycles report their complete chain. Enums may use a direct or aliased integer base and
retain symbolic values while objects lower to the primitive storage type:

```yaml
types:
  DeviceState:
    base: uint8
    enum:
      INIT: 0
      READY: 1
```

Enum values are checked against the exact signed/unsigned primitive range. Boolean,
real, string, and domain primitives cannot back schema-v1 enums.

## Reusable modules

Modules are loaded recursively from `Modules/<name>.yml`; the filename stem is their
identity namespace. Dependencies are resolved in deterministic dependency-first order,
equal transitive imports are deduplicated, and direct duplicates, missing modules,
parameter conflicts, and cycles fail with contextual diagnostics. Scalar parameters
are retained in the resolved graph as the schema-v1 extension point; Phase 4 does not
introduce a template language.

Type and object reference lookup is local-first. An unqualified imported name must be
unique, while an explicit name such as `CommonTypes.FirmwareVersion` or
`Diagnostics.supply_voltage` selects its namespace directly.

## Automatic addressing

Schema v1 partitions application indexes as follows:

| Category | Inclusive range |
| --- | --- |
| `telemetry` | `0x2000–0x27FF` |
| `command` | `0x2800–0x2FFF` |
| `configuration` | `0x3000–0x37FF` |
| `diagnostic` | `0x3800–0x3FFF` |

Automatic objects are sorted by qualified name. CanOpenGen computes unsigned IEEE
CRC-32 over the UTF-8 key `<category>:<qualified-name>`, maps it into the category
range, and linearly probes with wraparound until it finds a free index. All explicit
indexes are validated and reserved first. Records apply the same approach to fields in
subindices `0x01–0xFE`; arrays always use sequential subindices.

No persistent allocation lock exists. The same complete configuration always produces
the same map, while a semantic configuration change may change addresses in a collision
chain. Use an explicit index or subindex where strict stability is required.

Inspect the public CRC32 inputs independently:

```bash
canopengen address PressureSensor.pressure --category telemetry
canopengen address PressureSensor.pressure --category telemetry \
  --config Device/PressureSensor.yml
```

Development follows short-lived branches into `develop`, Conventional Commits, and
Semantic Versioning. See the [development workflow](docs/wiki/Development-Workflow.md)
and [architecture plan](docs/wiki/Architecture.md).

## Project status

Repository infrastructure, parsing, deterministic address allocation, alias/enum
lowering, recursive module/reference resolution, and Phase 5 EDS/Eds2Od generation are
implemented. Phase 6 adds Markdown documentation. The first stable release will be
`v1.0.0` only after the complete YAML-to-Eds2Od pipeline and its acceptance suite pass.

CanOpenGen is licensed under the [Apache License 2.0](LICENSE).
