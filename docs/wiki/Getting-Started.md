# Getting Started

CanOpenGen currently supports schema-v1 validation, recursive module loading,
namespace-aware alias/enum/reference resolution, and deterministic complete-device
address allocation on Linux with Python 3.11 or newer. From a checkout:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
git submodule update --init --recursive
canopengen validate Device/PressureSensor.yml
canopengen validate-all
canopengen map Device/PressureSensor.yml
canopengen generate Device/PressureSensor.yml --output build/canopen
```

`validate` checks YAML structure, the complete module graph, visible custom types,
symbolic PDO targets, PDO mappability/payload limits, and address semantics. `map` shows
resolved primitive/custom type metadata, all device/module objects, and address
provenance. `generate` writes a CiA 306 EDS, Markdown, and CANoopEn C++ Object Dictionary through the
bundled Eds2Od source project (which requires .NET SDK 10 when no native binary exists).
