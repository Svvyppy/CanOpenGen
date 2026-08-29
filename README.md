# CanOpenGen

CanOpenGen is an open-source, declarative CANopen Object Dictionary generator for
embedded projects using the CANoopEn C++ stack. A versioned YAML description will
become the single source of truth for validation, deterministic address allocation,
EDS generation, Markdown documentation, and CANoopEn C++ generation through Eds2Od.

> [!NOTE]
> Phase 1 provides schema-v1 structural validation and explicit raw models. Module,
> type, address, and PDO resolution plus output generation are not implemented yet.

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

## Structural validation

Every definition starts with `schema: 1` and contains exactly one `device` or `module`
identity. The current CLI validates YAML syntax and the public JSON Schema:

```bash
canopengen validate Device/PressureSensor.yml
canopengen validate-all
```

The example project demonstrates imports, parameter plumbing, aliases, enums,
variables, a record, an array, manual addresses, and symbolic TPDO/RPDO mappings.
These constructs are parsed into immutable raw models; cross-file and semantic checks
will be added in their dedicated phases.

The public IDE schema is [schemas/canopengen.schema.json](schemas/canopengen.schema.json).

Development follows short-lived branches into `develop`, Conventional Commits, and
Semantic Versioning. See the [development workflow](docs/wiki/Development-Workflow.md)
and [architecture plan](docs/wiki/Architecture.md).

## Project status

Repository infrastructure and Phase 1 raw parsing are implemented. Phase 2 adds
deterministic CRC32 address allocation. The first stable release will be `v1.0.0` only
after the complete YAML-to-Eds2Od pipeline and its acceptance suite pass.

CanOpenGen is licensed under the [Apache License 2.0](LICENSE).
