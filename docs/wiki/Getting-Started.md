# Getting Started

CanOpenGen currently supports schema-v1 validation, recursive module loading,
namespace-aware alias/enum/reference resolution, and deterministic complete-device
address allocation on Linux with Python 3.11 or newer. From a checkout:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
canopengen validate Device/PressureSensor.yml
canopengen validate-all
canopengen map Device/PressureSensor.yml
```

`validate` checks YAML structure, the complete module graph, visible custom types,
symbolic PDO targets, and currently available address semantics. `map` shows resolved
primitive/custom type metadata, all device/module objects, and address provenance. PDO
payload size/mappability and generated outputs arrive in later phases without changing
the schema-v1 command shape.
