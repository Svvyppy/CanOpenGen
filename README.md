# CanOpenGen

CanOpenGen is an open-source, declarative CANopen Object Dictionary generator for
embedded projects using the CANoopEn C++ stack. A versioned YAML description will
become the single source of truth for validation, deterministic address allocation,
EDS generation, Markdown documentation, and CANoopEn C++ generation through Eds2Od.

> [!NOTE]
> Phase 2 provides schema-v1 parsing and deterministic device-local address allocation.
> Module/type/PDO resolution and output generation are not implemented yet.

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
identity. The current CLI validates YAML syntax, the public JSON Schema, manual
addresses, and deterministic automatic allocation:

```bash
canopengen validate Device/PressureSensor.yml
canopengen validate-all
canopengen map Device/PressureSensor.yml
```

The example project demonstrates imports, parameter plumbing, aliases, enums,
variables, a record, an array, manual addresses, and symbolic TPDO/RPDO mappings.
These constructs are parsed into immutable models. Imported module objects and custom
type/PDO semantics will be added in their dedicated resolver phases.

The public IDE schema is [schemas/canopengen.schema.json](schemas/canopengen.schema.json).

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

Repository infrastructure, Phase 1 parsing, and Phase 2 deterministic address
allocation are implemented. Phase 3 resolves aliases and enums. The first stable
release will be `v1.0.0` only after the complete YAML-to-Eds2Od pipeline and its
acceptance suite pass.

CanOpenGen is licensed under the [Apache License 2.0](LICENSE).
