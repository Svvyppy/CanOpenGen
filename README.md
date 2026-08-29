# CanOpenGen

CanOpenGen is an open-source, declarative CANopen Object Dictionary generator for
embedded projects using the CANoopEn C++ stack. A versioned YAML description will
become the single source of truth for validation, deterministic address allocation,
EDS generation, Markdown documentation, and CANoopEn C++ generation through Eds2Od.

> [!NOTE]
> The project is in repository-bootstrap development. The generator and its CLI are
> not implemented yet.

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

Development follows short-lived branches into `develop`, Conventional Commits, and
Semantic Versioning. See the [development workflow](docs/wiki/Development-Workflow.md)
and [architecture plan](docs/wiki/Architecture.md).

## Project status

The implementation is intentionally phased. Repository infrastructure is Phase 0;
the data model and YAML parser begin in Phase 1. The first stable release will be
`v1.0.0` only after the complete YAML-to-Eds2Od pipeline and its acceptance suite pass.

CanOpenGen is licensed under the [Apache License 2.0](LICENSE).

